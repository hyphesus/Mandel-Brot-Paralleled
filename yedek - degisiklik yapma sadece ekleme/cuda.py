import numpy as np
from numba import cuda
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
from concurrent.futures import ProcessPoolExecutor
import os


def mandelbrot(c, max_iter):
    z = complex(0, 0)
    n = 0
    while abs(z) <= 2 and n < max_iter:
        z = z * z + c
        n += 1
    return n

def compute_mandelbrot_region(args):
    region_name, xmin, xmax, ymin, ymax, width, height, max_iter = args
    start_time = time.time()
    x = np.linspace(xmin, xmax, width)
    y = np.linspace(ymin, ymax, height)
    C = np.array(np.meshgrid(x, y)).T.reshape(-1, 2)
    C = C[:, 0] + 1j * C[:, 1]
    count = np.array([mandelbrot(c, max_iter) for c in C])
    elapsed_time = time.time() - start_time
    print(f"Region: {region_name}, Computation time: {elapsed_time:.2f} seconds, Process ID: {os.getpid()}")
    return count.reshape((height, width))

class ZoomableMandelbrot:
    def __init__(self, ax, max_iter, width=800, height=800):
        self.ax = ax
        self.max_iter = max_iter
        self.width = width
        self.height = height
        self.press = None
        self.xmin, self.xmax = -2.0, 2.0
        self.ymin, self.ymax = -2.0, 2.0

        self.cid_press = ax.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = ax.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = ax.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

        self.rect = patches.Rectangle((0,0), 0, 0, fill=False, edgecolor='white', linewidth=1.5)
        self.ax.add_patch(self.rect)
        self.plot_mandelbrot()

    def on_press(self, event):
        if event.inaxes != self.ax:
            return
        self.press = event.xdata, event.ydata
        self.rect.set_width(0)
        self.rect.set_height(0)
        self.rect.set_xy((event.xdata, event.ydata))

    def on_motion(self, event):
        if self.press is None or event.inaxes != self.ax:
            return
        xpress, ypress = self.press
        dx = event.xdata - xpress
        dy = event.ydata - ypress
        self.rect.set_width(dx)
        self.rect.set_height(dy)
        self.ax.figure.canvas.draw_idle()

    def on_release(self, event):
        if self.press is None or event.inaxes != self.ax:
            return
        xpress, ypress = self.press
        xrelease, yrelease = event.xdata, event.ydata
        self.xmin, self.xmax = sorted([xpress, xrelease])
        self.ymin, self.ymax = sorted([ypress, yrelease])
        self.press = None
        self.rect.set_width(0)
        self.rect.set_height(0)
        self.plot_mandelbrot()

    def plot_mandelbrot(self):
        start_time = time.time()

        # Split the image into four quadrants for parallel processing
        x_mid = (self.xmin + self.xmax) / 2
        y_mid = (self.ymin + self.ymax) / 2

        # Define regions for parallel computation
        regions = [
            ("Bottom-left", self.xmin, x_mid, self.ymin, y_mid, self.width // 2, self.height // 2, self.max_iter),
            ("Bottom-right", x_mid, self.xmax, self.ymin, y_mid, self.width // 2, self.height // 2, self.max_iter),
            ("Top-left", self.xmin, x_mid, y_mid, self.ymax, self.width // 2, self.height // 2, self.max_iter),
            ("Top-right", x_mid, self.xmax, y_mid, self.ymax, self.width // 2, self.height // 2, self.max_iter)
        ]

        # Adjust the order of regions for (1,2,3,4) grid layout
        # Swap regions for top-left and bottom-right quadrants
        regions[2], regions[1] = regions[1], regions[2]

        # Create a ProcessPoolExecutor
        processesNumber = 1
        with ProcessPoolExecutor(max_workers=processesNumber) as executor:
            # Map compute_mandelbrot_region to regions and collect results
            results = list(executor.map(compute_mandelbrot_region, regions))

        # Rearrange results to form the complete image
        bottom_left, bottom_right, top_left, top_right = results
        top = np.concatenate((top_left, top_right), axis=1)
        bottom = np.concatenate((bottom_left, bottom_right), axis=1)
        final_result = np.concatenate((bottom, top), axis=0)

        elapsed_time = time.time() - start_time
        print(f"Process count: {processesNumber} Computation time: {elapsed_time:.2f} seconds")


        self.ax.clear()
        self.ax.imshow(final_result.T, extent=[self.xmin, self.xmax, self.ymin, self.ymax], origin='lower', cmap='prism')
        self.ax.set_title(f"Process count: {processesNumber} Computation time: {elapsed_time:.2f} seconds")
        self.ax.axis("off")


        self.ax.figure.canvas.draw_idle()

def plot_zoomable_mandelbrot(max_iter):
    fig, ax = plt.subplots(figsize=(8, 8))
    zoomable_mandelbrot = ZoomableMandelbrot(ax, max_iter)
    plt.show()





#GPU İLE PARALELEŞTİRME

@cuda.jit(device=True)
def mandelbrot_cuda(c, max_iter):
    z = complex(0, 0)
    for n in range(max_iter):
        if abs(z) > 2:
            return n
        z = z*z + c
    return max_iter

@cuda.jit
def mandelbrot_kernel(min_x, max_x, min_y, max_y, width, height, image, max_iter):
    column, row = cuda.grid(2)
    if column < width and row < height:
        x = min_x + column * (max_x - min_x) / width
        y = min_y + row * (max_y - min_y) / height
        color = mandelbrot_cuda(complex(x, y), max_iter)
        image[row, column] = color

def compute_mandelbrot_gpu(min_x, max_x, min_y, max_y, width, height, max_iter):
    image = np.zeros((height, width), dtype=np.int32)
    threadsperblock = (16, 16)
    blockspergrid_x = (width + (threadsperblock[0] - 1)) // threadsperblock[0]
    blockspergrid_y = (height + (threadsperblock[1] - 1)) // threadsperblock[1]
    blockspergrid = (blockspergrid_x, blockspergrid_y)

    start_time = time.time()
    mandelbrot_kernel[blockspergrid, threadsperblock](min_x, max_x, min_y, max_y, width, height, image, max_iter)
    cuda.synchronize()
    elapsed_time = time.time() - start_time
    print(f"GPU computation time: {elapsed_time:.2f} seconds")

    return image

def plot_mandelbrot_gpu(max_iter=1000, width=1024, height=1024):
    fig, ax = plt.subplots(figsize=(10, 10))
    image = compute_mandelbrot_gpu(-2.0, 1.0, -1.5, 1.5, width, height, max_iter)
    ax.imshow(image, extent=[-2.0, 1.0, -1.5, 1.5], origin='lower', cmap='prism')
    plt.show()

# Guard for multiprocessing on Windows
if __name__ == '__main__':
    #plot_zoomable_mandelbrot(100)
    plot_mandelbrot_gpu(1000)