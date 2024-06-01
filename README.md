# Mandel-Brot-paralleled

This project's sole purpose is to  parallel calculate Mandelbrot sets with Cpu or Gpu. Some scripts here are prototypes, others are just the fun things we did along the way. The main.py is what you should be running if you want to launch this project. 

# It is powered by...

* matplotlib
* numpy
* tkinter
* cuda

# Why tkinter when you have matplotlib?

For potential. Nothing else besides that.

# How parallel is it?

Well, it divides the hole calculating section into 4 squares, aand calculates them one by one. As you may imagine, its not that good, but it is getting by.If you wanna improve, try dividing the whole canvas by some rows or columns (like, a lot of them).

# What is the Perfection.py and Elation do?

I dont know why i added that pixel art, but the Perfection.py is a Drag-With-Mouse program, which allows you to see all kinds of julia sets(almost). The sole purpose of this script is fun, and creating a possible puzzle game for my game project(s). 

