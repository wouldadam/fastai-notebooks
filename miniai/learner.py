# AUTOGENERATED! DO NOT EDIT! File to edit: ../15c-learner.ipynb.

# %% auto 0
__all__ = [
    "DataLoaders",
    "Callback",
    "CancelFitException",
    "CancelBatchException",
    "CancelEpochException",
    "run_cbs",
    "DeviceCB",
    "to_cpu",
    "MetricsCB",
    "with_cbs",
    "Learner",
    "TrainCB",
    "ProgressCB",
    "MomentumLearner",
    "LRFinderCB",
]

# %% ../15c-learner.ipynb 1
import math
from copy import copy
from operator import attrgetter
from collections.abc import Mapping
from functools import partial

import torch
from torch import optim

from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import ExponentialLR

from torcheval.metrics import Mean

import fastcore.all as fc
from fastprogress import progress_bar, master_bar

import matplotlib.pyplot as plt

import miniai.datasets as ds
import miniai.conv as cv


# %% ../15c-learner.ipynb 8
class DataLoaders:
    """Holds training and validation dataloaders."""

    def __init__(self, *dls):
        """Accepts a train and valid dataloader."""
        self.train, self.valid = dls[:2]

    @classmethod
    def from_dsd(cls, dsd, batch_size, num_workers=4):
        """Create dataloaders from a dataset dict."""
        return cls(
            *[
                DataLoader(
                    d,
                    batch_size,
                    num_workers=num_workers,
                    collate_fn=ds.collate_dict(d),
                )
                for d in dsd.values()
            ]
        )


# %% ../15c-learner.ipynb 14
# Base class for all callbacks
class Callback:
    order = 0


# Exceptions thrown by Callbacks exception occurs in the related function
class CancelFitException(Exception):
    pass


class CancelBatchException(Exception):
    pass


class CancelEpochException(Exception):
    pass


# Runs the given method on all callbacks in order
def run_cbs(cbs, method_name):
    for cb in sorted(cbs, key=attrgetter("order")):
        method = getattr(cb, method_name, None)
        if method is not None:
            method()


# %% ../15c-learner.ipynb 19
class DeviceCB(Callback):
    def __init__(self, device=cv.def_device):
        fc.store_attr()

    """Moves the model to the device before fitting and the batch before each batch."""

    def before_fit(self):
        self.learn.model.to(self.device)

    def before_batch(self):
        self.learn.batch = cv.to_device(self.learn.batch, device=self.device)


# %% ../15c-learner.ipynb 29
def to_cpu(x):
    """Takes maps, lists and tuples of tensors or just tensors and moves them to the cpu"""
    if isinstance(x, Mapping):
        return {k: to_cpu(v) for k, v in x.items()}
    if isinstance(x, list):
        return [to_cpu(o) for o in x]
    if isinstance(x, tuple):
        return tuple(to_cpu(list(x)))

    res = x.detach().cpu()
    return res.float() if res.dtype == torch.float16 else res


class MetricsCB(Callback):
    """Tracks a set of metrics + a loss (weighted avg of the losses)."""

    def __init__(self, *pos_metrics, **metrics):
        # Positional args become metrics named after the type of the class
        for metric in pos_metrics:
            metrics[type(metric).__name__] = metric

        self.metrics = metrics
        self.loss = Mean()

        self.all_metrics = copy(metrics)
        self.all_metrics["loss"] = self.loss

    def _log(self, data):
        print(data)

    def before_fit(self):
        self.learn.metrics = self

    def before_epoch(self):
        for metric in self.all_metrics.values():
            metric.reset()

    def after_epoch(self):
        data = {
            "epoch": self.learn.epoch,
            "train": "train" if self.learn.model.training else "eval",
        }

        for name, metric in self.all_metrics.items():
            data[name] = f"{metric.compute():.3f}"

        self._log(data)

    def after_batch(self):
        # We need to make sure all tensors are on the same device so just move them to the CPU
        x, y = to_cpu(self.learn.batch)
        preds = to_cpu(self.learn.preds)
        loss = to_cpu(self.learn.loss)

        # Update all of the metrics
        for metric in self.metrics.values():
            metric.update(preds, y)

        # Update our loss
        self.loss.update(loss, weight=len(x))


# %% ../15c-learner.ipynb 32
class with_cbs:
    """
    Decorator that adds before and after callbacks to a function.
    If an exception is thrown then a cleanup_* callback is called.
    """

    def __init__(self, name):
        self.name = name

    def __call__(self, fn):
        def _fn(o, *args, **kwargs):
            try:
                o.callback(f"before_{self.name}")
                fn(o, *args, **kwargs)
                o.callback(f"after_{self.name}")
            except globals()[f"Cancel{self.name.title()}Exception"]:
                pass
            finally:
                o.callback(f"cleanup_{self.name}")

        return _fn


# %% ../15c-learner.ipynb 33
class Learner:
    def __init__(self, model, dls, loss_func, lr, callbacks, opt_func=optim.SGD):
        fc.store_attr()
        for cb in self.callbacks:
            cb.learn = self

    @with_cbs("batch")
    def one_batch(self):
        """Run one training/validation for one batch of data."""
        self.predict()
        self.calc_loss()

        if self.model.training:
            self.backward()
            self.step()
            self.zero_grad()

    def one_epoch(self, train):
        """Run a single epoch of training or validation."""
        self.model.train(train)
        self.dl = self.dls.train if train else self.dls.valid

        self._one_epoch()

    @with_cbs("epoch")
    def _one_epoch(self):
        for self.num, self.batch in enumerate(self.dl):
            self.one_batch()

    def fit(self, n_epochs):
        """Run training and validation for a number of epochs."""
        self.n_epochs = n_epochs
        self.epochs = range(n_epochs)
        self.opt = self.opt_func(self.model.parameters(), self.lr)

        self._fit()

    @with_cbs("fit")
    def _fit(self):
        for self.epoch in self.epochs:
            self.one_epoch(True)
            self.one_epoch(False)

    def __getattr__(self, name):
        # If these methods dont exist, we are going to defer them to our callbacks
        # so we return a partial that calls our callback fn.
        if name in ("predict", "calc_loss", "backward", "step", "zero_grad"):
            return partial(self.callback, name)

        raise AttributeError(name)

    def callback(self, method_name):
        """ "Go through callbacks, sorted by the order attribute and call their relavant method name."""
        run_cbs(self.callbacks, method_name)


# This means we'll need a TrainCB to make things work
class TrainCB(Callback):
    def predict(self):
        self.learn.preds = self.learn.model(self.learn.batch[0])

    def calc_loss(self):
        self.learn.loss = self.learn.loss_func(self.learn.preds, self.learn.batch[1])

    def backward(self):
        self.learn.loss.backward()

    def step(self):
        self.learn.opt.step()

    def zero_grad(self):
        self.learn.opt.zero_grad()


# %% ../15c-learner.ipynb 36
class ProgressCB(Callback):
    order = MetricsCB.order + 1

    def __init__(self, plot=False):
        fc.store_attr()

    def before_fit(self):
        # Change the epochs to a progress bar around a range
        self.bar = master_bar(self.learn.epochs)
        self.learn.epochs = self.bar
        self.losses = []

    def before_epoch(self):
        # Wrap the dataloaders in a progress bar
        self.learn.dl = progress_bar(self.learn.dl, leave=False, parent=self.bar)

    def after_batch(self):
        # Set the progresss bars comment to be the current loss
        self.learn.dl.comment = f"{self.learn.loss:.3f}"

        # Update the plot if requested
        if self.plot and self.learn.model.training:
            self.losses.append(self.learn.loss.item())
            self.bar.update_graph([[fc.L.range(self.losses), self.losses]])


# %% ../15c-learner.ipynb 39
class MomentumLearner(Learner):
    """
    Our MomentumLearner behaves a bit differently.
    Instead of zeroing the gradient in zero_grad it multiplies them by a number (generally < 1).
    This means that the previous gradients still exist but in a reduced form,
    giving the learner "momentum".
    """

    def __init__(self, model, dls, loss_func, lr, callbacks, opt_func=optim.SGD, momentum=0.85):
        self.momentum = momentum
        super().__init__(model, dls, loss_func, lr, callbacks, opt_func)

    def predict(self):
        self.preds = self.model(self.batch[0])

    def calc_loss(self):
        self.loss = self.loss_func(self.preds, self.batch[1])

    def backward(self):
        self.loss.backward()

    def step(self):
        self.opt.step()

    def zero_grad(self):
        with torch.no_grad():
            for p in self.model.parameters():
                p.grad *= self.momentum


# %% ../15c-learner.ipynb 45
class LRFinderCB(Callback):
    def __init__(self, gamma=1.3):
        fc.store_attr()

    def before_fit(self):
        # Create a new LR scheduler
        self.sched = ExponentialLR(self.learn.opt, self.gamma)

        # We are going to track learning rates and losses
        self.lrs = []
        self.losses = []

        # And the min loss
        self.min = math.inf

    def after_batch(self):
        # If we are not training then stop
        if not self.learn.model.training:
            raise CancelEpochException()

        self.lrs.append(self.learn.opt.param_groups[0]["lr"])
        loss = to_cpu(self.learn.loss)
        self.losses.append(loss)

        if loss < self.min:
            self.min = loss

        # Stop training if the loss is 3x our min loss
        if loss > self.min * 3:
            raise CancelFitException()

        # Run 1 step of the scheduler
        self.sched.step()

    def cleanup_fit(self):
        plt.plot(self.lrs, self.losses)
        plt.xscale("log")
