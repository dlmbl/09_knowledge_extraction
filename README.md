# Exercise 9: Explainable AI and Knowledge Extraction

## Overview
The goal of this exercise is to learn how to probe what a pre-trained classifier has learned about the data it was trained on. 

We will be working with a simple example which is a fun derivation on the MNIST dataset that you will have seen in previous exercises in this course. 
Unlike regular MNIST, our dataset is classified not by number, but by color!

![CMNIST](assets/cmnist.png)

In this exercise, we will return to conventional, gradient-based attribution methods to see what they can tell us about what the classifier knows. 
We will see that, even for such a simple problem, there is some information that these methods do not give us. 

We will then train a generative adversarial network, or GAN, to try to create counterfactual images. 
These images are modifications of the originals, which are able to fool the classifier into thinking they come from a different class!. 
We will evaluate this GAN using our classifier; Is it really able to change an image's class in a meaningful way? 

Finally, we will combine the two methods — attribution and counterfactual — to get a full explanation of what exactly it is that the classifier is doing. We will likely learn whether it can teach us anything, and whether we should trust it!

If time permits, we will try to apply this all over again as a bonus exercise to a much more complex and more biologically relevant problem.

![synister](assets/synister.png)
## Setup

Before anything else, in the super-repository called `DL-MBL-2024`:
```
git pull
git submodule update --init 08_knowledge_extraction
```

Then, if you have any other exercises still running, please save your progress and shut down those kernels.
This is a GPU-hungry exercise so you're going to need all the GPU memory you can get.

Next, run the setup script. It might take a few minutes.
```
cd 08_knowledge_extraction
source setup.sh
```
This will:
- Create a `mamba` environment for this exercise
- Download and unzip data and pre-trained network
Feel free to have a look at the `setup.sh` script to see the details.


Next, begin a Jupyter Lab instance:
```
jupyter lab
```
...and continue with the instructions in the notebook.


### Acknowledgments

This notebook was written by Jan Funke and modified by Tri Nguyen and Diane Adjavon, using code from Nils Eckstein and a modified version of the [CycleGAN](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) implementation.
