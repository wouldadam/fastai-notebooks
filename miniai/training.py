# AUTOGENERATED! DO NOT EDIT! File to edit: ../14-minibatch-training.ipynb.

# %% auto 0
__all__ = ["accuracy", "Dataset", "fit", "get_dls"]

# %% ../14-minibatch-training.ipynb 1
import torch
from torch.utils.data import DataLoader


# %% ../14-minibatch-training.ipynb 23
# We can use it to calculate accuracy, this isnt needed for the NN but helps us understand whats going on
def accuracy(out, targets):
    return (out.argmax(dim=1) == targets).float().mean()


# %% ../14-minibatch-training.ipynb 44
class Dataset:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __len__(self):
        return len(self.x)

    def __getitem__(self, i):
        return self.x[i], self.y[i]


# %% ../14-minibatch-training.ipynb 60
def fit(epochs, model, loss_func, opt, train_dl, valid_dl):
    for epoch in range(epochs):
        # Some layers behave differently during training and validation so we have to tell them
        model.train()
        for batch_inp, batch_targets in train_dl:
            # Run the model
            preds = model(batch_inp)
            loss = loss_func(preds, batch_targets)

            loss.backward()

            # Update the weights
            opt.step()
            opt.zero_grad()

        # Now run the validation set
        model.eval()
        with torch.no_grad():
            total_loss = 0.0
            total_acc = 0.0
            count = 0

            for batch_inp, batch_targets in train_dl:
                preds = model(batch_inp)

                count += len(batch_inp)
                total_loss += loss_func(preds, batch_targets).item() * len(batch_inp)
                total_acc += accuracy(preds, batch_targets).item() * len(batch_inp)

        total_loss /= count
        total_acc /= count
        print(f"epoch: {epoch}, loss: {total_loss}, acc: {total_acc}")

    return total_loss, total_acc


def get_dls(train_ds, valid_ds, batch_size, **kwargs):
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True, **kwargs),
        DataLoader(valid_ds, batch_size=batch_size * 2, **kwargs),
    )
