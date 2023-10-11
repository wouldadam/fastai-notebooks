# AUTOGENERATED! DO NOT EDIT! File to edit: ../14-huggingface-datasets.ipynb.

# %% auto 0
__all__ = ["show_image", "subplots", "get_grid", "show_images"]

# %% ../14-huggingface-datasets.ipynb 1
import math
from itertools import zip_longest

import numpy as np
import matplotlib.pyplot as plt
import fastcore.all as fc


# %% ../14-huggingface-datasets.ipynb 19
@fc.delegates(plt.Axes.imshow)  # kwargs is going to imshow
def show_image(img, ax=None, figsize=None, title=None, **kwargs):
    """Show A PIL or PyTorch image on 'ax'."""

    # If its on the GPU copy to CPU
    if fc.hasattrs(img, ("cpu", "permute")):
        img = img.cpu()

        # Ensure correct axis order
        if img.shape[0] < 5:
            img = img.permute(1, 2, 0)
    elif not isinstance(img, np.ndarray):
        # If not a numpy array make it one
        img = np.array(img)

    if img.shape[-1] == 1:
        img = img[..., 0]

    # Create axis if not specified
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)

    ax.imshow(img, **kwargs)

    if title is not None:
        ax.set_title(title)

    ax.axis("off")  # Remove axis ticks
    return ax


# %% ../14-huggingface-datasets.ipynb 23
@fc.delegates(plt.subplots, keep=True)
def subplots(
    nrows: int = 1,  # Number of rows in returned axes grid
    ncols: int = 1,  # Number of columns in returned axes grid
    figsize: tuple = None,  # Width, height in inches of the returned figure
    imsize: int = 3,  # Size (in inches) of images that will be displayed in the returned figure
    suptitle: str = None,  # Title to be set to returned figure
    **kwargs,
):
    """A figure and set of subplots to display images of `imsize` inches"""
    if figsize is None:
        figsize = (ncols * imsize, nrows * imsize)

    fig, ax = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)

    if suptitle is not None:
        fig.suptitle(suptitle)

    if nrows * ncols == 1:
        ax = np.array([ax])

    return fig, ax


# %% ../14-huggingface-datasets.ipynb 26
@fc.delegates(subplots)
def get_grid(
    n: int,  # Number of axes
    nrows: int = None,  # Number of rows, defaulting to `int(math.sqrt(n))`
    ncols: int = None,  # Number of columns, defaulting to `ceil(n/rows)`
    title: str = None,  # If passed, title set to the figure
    weight: str = "bold",  # Title font weight
    size: int = 14,  # Title font size
    **kwargs,
):
    "Return a grid of `n` axes, `rows` by `cols`"
    if nrows:
        ncols = ncols or int(np.ceil(n / nrows))
    elif ncols:
        nrows = nrows or int(np.ceil(n / ncols))
    else:
        nrows = int(math.sqrt(n))
        ncols = int(np.floor(n / nrows))

    print(nrows, ncols)

    fig, axs = subplots(nrows, ncols, **kwargs)

    for i in range(n, nrows * ncols):
        axs.flat[i].set_axis_off()

    if title is not None:
        fig.suptitle(title, weight=weight, size=size)

    return fig, axs


# %% ../14-huggingface-datasets.ipynb 28
@fc.delegates(subplots)
def show_images(
    ims: list,  # Images to show
    nrows: int | None = None,  # Number of rows in grid
    ncols: int | None = None,  # Number of columns in grid (auto-calculated if None)
    titles: list | None = None,  # Optional list of titles for each image
    **kwargs,
):
    """ "Show all images `ims` as subplots with `rows` using `titles`"""

    axs = get_grid(len(ims), nrows, ncols, **kwargs)[1].flat

    for im, t, ax in zip_longest(ims, titles or [], axs):
        show_image(im, ax=ax, title=t)
