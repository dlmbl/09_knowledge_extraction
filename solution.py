# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# # Exercise 8: Knowledge Extraction from a Convolutional Neural Network
#
# In the following exercise we will train a convolutional neural network to classify electron microscopy images of Drosophila synapses, based on which neurotransmitter they contain. We will then train a CycleGAN and use a method called Discriminative Attribution from Counterfactuals (DAC) to understand how the network performs its classification, effectively going back from prediction to image data.
#
# ### Acknowledgments
#
# This notebook was written by Jan Funke and modified by Tri Nguyen and Diane Adjavon, using code from Nils Eckstein and a modified version of the [CycleGAN](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) implementation.
#
# %% [markdown]
# <div class="alert alert-danger">
# Set your python kernel to <code>08_knowledge_extraction</code>
# </div>

# %% [markdown]
# <div class="alert alert-block alert-success"><h1>Start here (AKA checkpoint 0)</h1>
#
# </div>

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# # Part 1: Setup
#
# In this part of the notebook, we will load the same dataset as in the previous exercise.
# We will also learn to load one of our trained classifiers from a checkpoint.
# %%
# loading the data
from classifier.data import ColoredMNIST

mnist = ColoredMNIST("data", download=True)
# %% [markdown]
# Here's a quick reminder about the dataset:
# - The dataset is a colored version of the MNIST dataset.
# - Instead of using the digits as classes, we use the colors.
# - There are four classes named after the matplotlib colormaps from which we sample the data: spring, summer, autumn, and winter.
# Let's plot a few examples.
# %%
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Show some examples
fig, axs = plt.subplots(4, 4, figsize=(8, 8))
for i, ax in enumerate(axs.flatten()):
    x, y = mnist[i]
    x = x.permute((1, 2, 0))  # make channels last
    ax.imshow(x)
    ax.set_title(f"Class {y}")
    ax.axis("off")


# TODO move this to the "classification" exercise
# TODO modify so that we can show examples as well at different places in the range
def plot_color_gradients(cmap_list):
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    # Create figure and adjust figure height to number of colormaps
    nrows = len(cmap_list)
    figh = 0.35 + 0.15 + (nrows + (nrows - 1) * 0.1) * 0.22
    fig, axs = plt.subplots(nrows=nrows + 1, figsize=(6.4, figh))
    fig.subplots_adjust(top=1 - 0.35 / figh, bottom=0.15 / figh, left=0.2, right=0.99)

    for ax, name in zip(axs, cmap_list):
        ax.imshow(gradient, aspect="auto", cmap=mpl.colormaps[name])
        ax.text(
            -0.01,
            0.5,
            name,
            va="center",
            ha="right",
            fontsize=10,
            transform=ax.transAxes,
        )

    # Turn off *all* ticks & spines, not just the ones with colormaps.
    for ax in axs:
        ax.set_axis_off()


plot_color_gradients(["spring", "summer", "winter", "autumn"])
# %% [markdown]
# In the Failure Modes exercise, we trained a classifier on this dataset. Let's load that classifier now!
#
# TODO add a task
# %%
import torch
from classifier.model import DenseModel

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# TODO modify this with the location of your classifier checkpoint
checkpoint = torch.load("extras/checkpoints/model.pth")

# Load the model
model = DenseModel(input_shape=(3, 28, 28), num_classes=4)
model.load_state_dict(checkpoint)
model = model.to(device)

# %% [markdown]
# # Part 2: Masking the relevant part of the image
#
# In this section we will make a first attempt at highlight differences between the "real" and "fake" images that are most important to change the decision of the classifier.
#

# %% [markdown]
# ## Attributions through integrated gradients
#
# Attribution is the process of finding out, based on the output of a neural network, which pixels in the input are (most) responsible. Another way of thinking about it is: which pixels would need to change in order for the network's output to change.
#
# Here we will look at an example of an attribution method called [Integrated Gradients](https://captum.ai/docs/extension/integrated_gradients). If you have a bit of time, have a look at this [super fun exploration of attribution methods](https://distill.pub/2020/attribution-baselines/), especially the explanations on Integrated Gradients.

# %% editable=true slideshow={"slide_type": ""} tags=[]
batch_size = 4
batch = [mnist[i] for i in range(batch_size)]
x = torch.stack([b[0] for b in batch])
y = torch.tensor([b[1] for b in batch])
x = x.to(device)
y = y.to(device)

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-info"><h3>Task 2.1 Get an attribution</h3>
#
# In this next part, we will get attributions on single batch. We use a library called [captum](https://captum.ai), and focus on the `IntegratedGradients` method.
# Create an `IntegratedGradients` object and run attribution on `x,y` obtained above.
#
# </div>

# %% editable=true slideshow={"slide_type": ""} tags=[]
from captum.attr import IntegratedGradients

############### Task 2.1 TODO ############
# Create an integrated gradients object.
integrated_gradients = ...

# Generated attributions on integrated gradients
attributions = ...

# %% editable=true slideshow={"slide_type": ""} tags=["solution"]
#########################
# Solution for Task 2.1 #
#########################

from captum.attr import IntegratedGradients

# Create an integrated gradients object.
integrated_gradients = IntegratedGradients(model)

# Generated attributions on integrated gradients
attributions = integrated_gradients.attribute(x, target=y)

# %% editable=true slideshow={"slide_type": ""} tags=[]
attributions = (
    attributions.cpu().numpy()
)  # Move the attributions from the GPU to the CPU, and turn then into numpy arrays for future processing

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# Here is an example for an image, and its corresponding attribution.


# %% editable=true slideshow={"slide_type": ""} tags=[]
from captum.attr import visualization as viz


def visualize_attribution(attribution, original_image):
    attribution = np.transpose(attribution, (1, 2, 0))
    original_image = np.transpose(original_image, (1, 2, 0))

    viz.visualize_image_attr_multiple(
        attribution,
        original_image,
        methods=["original_image", "heat_map"],
        signs=["all", "absolute_value"],
        show_colorbar=True,
        titles=["Image", "Attribution"],
        use_pyplot=True,
    )


# %% editable=true slideshow={"slide_type": ""} tags=[]
for attr, im in zip(attributions, x.cpu().numpy()):
    visualize_attribution(attr, im)

# %% [markdown]
#
# The attributions are shown as a heatmap. The brighter the pixel, the more important this attribution method thinks that it is.
# As you can see, it is pretty good at recognizing the number within the image.
# As we know, however, it is not the digit itself that is important for the classification, it is the color!
# Although the method is picking up really well on the region of interest, it would be difficult to conclude from this that it is the color that matters.


# %% [markdown]
# Something is slightly unfair about this visualization though.
# We are visualizing as if it were grayscale, but both our images and our attributions are in color!
# Can we learn more from the attributions if we visualize them in color?
# %%
def visualize_color_attribution(attribution, original_image):
    attribution = np.transpose(attribution, (1, 2, 0))
    original_image = np.transpose(original_image, (1, 2, 0))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    ax1.imshow(original_image)
    ax1.set_title("Image")
    ax1.axis("off")
    ax2.imshow(np.abs(attribution))
    ax2.set_title("Attribution")
    ax2.axis("off")
    plt.show()


for attr, im in zip(attributions, x.cpu().numpy()):
    visualize_color_attribution(attr, im)

# %% [markdown]
# We get some better clues when looking at the attributions in color.
# The highlighting doesn't just happen in the region with number, but also seems to hapen in a channel that matches the color of the image.
# Just based on this, however, we don't get much more information than we got from the images themselves.
#
# If we didn't know in advance, it is unclear whether the color or the number is the most important feature for the classifier.
# %% [markdown]
#
# ### Changing the basline
#
# Many existing attribution algorithms are comparative: they show which pixels of the input are responsible for a network output *compared to a baseline*.
# The baseline is often set to an all 0 tensor, but the choice of the baseline affects the output.
# (For an interactive illustration of how the baseline affects the output, see [this Distill paper](https://distill.pub/2020/attribution-baselines/))
#
# You can change the baseline used by the `integrated_gradients` object.
#
# Use the command:
# ```
# ?integrated_gradients.attribute
# ```
# To get more details about how to include the baseline.
#
# Try using the code above to change the baseline and see how this affects the output.
#
# 1. Random noise as a baseline
# 2. A blurred/noisy version of the original image as a baseline.

# %% [markdown]
# <div class="alert alert-block alert-info"><h4>Task 2.3: Use random noise as a baseline</h4>
#
# Hint: `torch.rand_like`
# </div>

# %% editable=true slideshow={"slide_type": ""} tags=[]
# Baseline
random_baselines = ...  # TODO Change
# Generate the attributions
attributions_random = integrated_gradients.attribute(...)  # TODO Change

# Plotting
for attr, im in zip(attributions_random.cpu().numpy(), x.cpu().numpy()):
    visualize_attribution(attr, im)

# %% editable=true slideshow={"slide_type": ""} tags=["solution"]
#########################
# Solution for task 2.3 #
#########################
# Baseline
random_baselines = torch.rand_like(x)
# Generate the attributions
attributions_random = integrated_gradients.attribute(
    x, target=y, baselines=random_baselines
)

# Plotting
for attr, im in zip(attributions_random.cpu().numpy(), x.cpu().numpy()):
    visualize_color_attribution(attr, im)

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-info"><h4>Task 2.4: Use a blurred image a baseline</h4>
#
# Hint: `torchvision.transforms.functional` has a useful function for this ;)
# </div>

# %% editable=true slideshow={"slide_type": ""} tags=[]
# TODO Import required function

# Baseline
blurred_baselines = ...  # TODO Create blurred version of the images
# Generate the attributions
attributions_blurred = integrated_gradients.attribute(...)  # TODO Fill

# Plotting
for attr, im in zip(attributions_blurred.cpu().numpy(), x.cpu().numpy()):
    visualize_color_attribution(attr, im)

# %% editable=true slideshow={"slide_type": ""} tags=["solution"]
#########################
# Solution for task 2.4 #
#########################
from torchvision.transforms.functional import gaussian_blur

# Baseline
blurred_baselines = gaussian_blur(x, kernel_size=(5, 5))
# Generate the attributions
attributions_blurred = integrated_gradients.attribute(
    x, target=y, baselines=blurred_baselines
)

# Plotting
for attr, im in zip(attributions_blurred.cpu().numpy(), x.cpu().numpy()):
    visualize_color_attribution(attr, im)

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="altert alert-block alert-warning"><h4> Questions </h4>
# TODO change these questions now!!
# - Are any of the features consistent across baselines? Why do you think that is?
# - What baseline do you like best so far? Why?
# - If you were to design an ideal baseline, what would you choose?
# </div>

# %% [markdown]
# <div class="alert alert-block alert-info"><h2>BONUS Task: Using different attributions.</h2>
#
#
#
# [`captum`](https://captum.ai/tutorials/Resnet_TorchVision_Interpret) has access to various different attribution algorithms.
#
# Replace `IntegratedGradients` with different attribution methods. Are they consistent with each other?
# </div>

# %% [markdown]
# <div class="alert alert-block alert-success"><h2>Checkpoint 2</h2>
# Let us know on the exercise chat when you've reached this point!
#
# TODO change this!!
#
# At this point we have:
#
# - Trained a classifier that can predict neurotransmitters from EM-slices of synapses.</li>
# - Found a way to mask the parts of the image that seem to be relevant for the classification, using integrated gradients.</li>
# - Discovered the effect of changing the baseline on the output of integrated gradients.
#
# Coming up in the next section, we will learn how to create counterfactual images.
# These images will change *only what is necessary* in order to change the classification of the image.
# We'll see that using counterfactuals we will be able to disambiguate between color and number as an important feature.
# </div>


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# # Part 3: Train a GAN to Translate Images
#
# To gain insight into how the trained network classify images, we will use [Discriminative Attribution from Counterfactuals](https://arxiv.org/abs/2109.13412), a feature attribution with counterfactual explanations methodology.
# This method employs a CycleGAN to translate images from one class to another to make counterfactual explanations
#
# **What is a counterfactual?**
#
# You've learned about adversarial examples in the lecture on failure modes. These are the imperceptible or noisy changes to an image that drastically changes a classifier's opinion.
# Counterfactual explanations are the useful cousins of adversarial examples. They are *perceptible* and *informative* changes to an image that changes a classifier's opinion.
#
# In the image below you can see the difference between the two. In the first column are MNIST images along with their classifictaions, and in the second column are counterfactual explanations to *change* that class. You can see that in both cases a human being would (hopefully) agree with the new classification. By comparing the two columns, we can therefore begin to define what makes each digit special.
#
# In contrast, the third and fourth columns show an MNIST image and a corresponding adversarial example. Here the network returns a prediction that most human beings (who aren't being facetious) would strongly disagree with.
#
# <img src="assets/ce_vs_ae.png" width=50% />
#
# **Counterfactual synapses**
#
# In this example, we will train a CycleGAN network that translates GABAergic synapses to acetylcholine synapses (you can also train other pairs too by changing the classes below).

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ### The model
# TODO Change this!!
# ![cycle.png](assets/cyclegan.png)
#
# In the following, we create a [CycleGAN model](https://arxiv.org/pdf/1703.10593.pdf). It is a Generative Adversarial model that is trained to turn one class of images X (for us, GABA) into a different class of images Y (for us, Acetylcholine).
#
# It has two generators:
#    - Generator G takes a GABA image and tries to turn it into an image of an Acetylcholine synapse. When given an image that is already showing an Acetylcholine synapse, G should just re-create the same image: these are the `identities`.
#    - Generator F takes a Acetylcholine image and tries to turn it into an image of an GABA synapse. When given an image that is already showing a GABA synapse, F should just re-create the same image: these are the `identities`.
#
#
# When in training mode, the CycleGAN will also create a `reconstruction`. These are images that are passed through both generators.
# For example, a GABA image will first be transformed by G to Acetylcholine, then F will turn it back into GABA.
# This is achieved by training the network with a cycle-consistency loss. In our example, this is an L2 loss between the `real` GABA image and the `reconstruction` GABA image.
#
# But how do we force the generators to change the class of the input image? We use a discriminator for each.
#    - DX tries to recognize fake GABA images: F will need to create images realistic and GABAergic enough to trick it.
#    - DY tries to recognize fake Acetylcholine images: G will need to create images realistic and cholinergic enough to trick it.

# %%
from dlmbl_unet import UNet
from torch import nn


class Generator(nn.Module):
    def __init__(self, generator, style_mapping):
        super().__init__()
        self.generator = generator
        self.style_mapping = style_mapping

    def forward(self, x, y):
        """
        x: torch.Tensor
            The source image
        y: torch.Tensor
            The style image
        """
        style = self.style_mapping(y)
        # Concatenate the style vector with the input image
        style = style.unsqueeze(-1).unsqueeze(-1)
        style = style.expand(-1, -1, x.size(2), x.size(3))
        x = torch.cat([x, style], dim=1)
        return self.generator(x)


# TODO make them figure out how many channels in the input and output, make them choose UNet depth
unet = UNet(depth=2, in_channels=6, out_channels=3, final_activation=nn.Sigmoid())
discriminator = DenseModel(input_shape=(3, 28, 28), num_classes=4)
style_mapping = DenseModel(input_shape=(3, 28, 28), num_classes=3)
generator = Generator(unet, style_mapping=style_mapping)

# all models on the GPU
generator = generator.to(device)
discriminator = discriminator.to(device)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ## Training a GAN
#
# Yes, really!
#
# TODO about the losses:
# - An adversarial loss
# - A cycle loss
# TODO add exercise!

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-banner alert-info"><h4>Task 3.2: Training!</h4>
# Let's train the CycleGAN one batch a time, plotting the output every so often to see how it is getting on.
#
# While you watch the model train, consider whether you think it will be successful at generating counterfactuals in the number of steps we give it. What is the minimum number of iterations you think are needed for this to work, and how much time do yo uthink it will take?
# </div>


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ...this time again.
#
# <img src="assets/model_train.jpg" alt="drawing" width="500px"/>

# TODO also turn this into a standalong script for use during the project phase
from torch.utils.data import DataLoader
from tqdm import tqdm


def set_requires_grad(module, value=True):
    """Sets `requires_grad` on a `module`'s parameters to `value`"""
    for param in module.parameters():
        param.requires_grad = value


cycle_loss_fn = nn.L1Loss()
class_loss_fn = nn.CrossEntropyLoss()

optimizer_d = torch.optim.Adam(discriminator.parameters(), lr=1e-6)
optimizer_g = torch.optim.Adam(generator.parameters(), lr=1e-4)

dataloader = DataLoader(
    mnist, batch_size=32, drop_last=True, shuffle=True
)  # We will use the same dataset as before

losses = {"cycle": [], "adv": [], "disc": []}
for epoch in range(50):
    for x, y in tqdm(dataloader, desc=f"Epoch {epoch}"):
        x = x.to(device)
        y = y.to(device)
        # get the target y by shuffling the classes
        # get the style sources by random sampling
        random_index = torch.randperm(len(y))
        x_style = x[random_index].clone()
        y_target = y[random_index].clone()

        set_requires_grad(generator, True)
        set_requires_grad(discriminator, False)
        optimizer_g.zero_grad()
        # Get the fake image
        x_fake = generator(x, x_style)
        # Try to cycle back
        x_cycled = generator(x_fake, x)
        # Discriminate
        discriminator_x_fake = discriminator(x_fake)
        # Losses to  train the generator

        # 1. make sure the image can be reconstructed
        cycle_loss = cycle_loss_fn(x, x_cycled)
        # 2. make sure the discriminator is fooled
        adv_loss = class_loss_fn(discriminator_x_fake, y_target)

        # Optimize the generator
        (cycle_loss + adv_loss).backward()
        optimizer_g.step()

        set_requires_grad(generator, False)
        set_requires_grad(discriminator, True)
        optimizer_d.zero_grad()
        # TODO Do I need to re-do the forward pass?
        discriminator_x = discriminator(x)
        discriminator_x_fake = discriminator(x_fake.detach())
        # Losses to train the discriminator
        # 1. make sure the discriminator can tell real is real
        real_loss = class_loss_fn(discriminator_x, y)
        # 2. make sure the discriminator can't tell fake is fake
        fake_loss = -class_loss_fn(discriminator_x_fake, y_target)
        #
        disc_loss = (real_loss + fake_loss) * 0.5
        disc_loss.backward()
        # Optimize the discriminator
        optimizer_d.step()

        losses["cycle"].append(cycle_loss.item())
        losses["adv"].append(adv_loss.item())
        losses["disc"].append(disc_loss.item())

# %%
plt.plot(losses["cycle"], label="Cycle loss")
plt.plot(losses["adv"], label="Adversarial loss")
plt.plot(losses["disc"], label="Discriminator loss")
plt.legend()
plt.show()
# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# Let's add a quick plotting function before we begin training...

# %%
idx = 0
fig, axs = plt.subplots(1, 4, figsize=(12, 4))
axs[0].imshow(x[idx].cpu().permute(1, 2, 0).detach().numpy())
axs[1].imshow(x_style[idx].cpu().permute(1, 2, 0).detach().numpy())
axs[2].imshow(x_fake[idx].cpu().permute(1, 2, 0).detach().numpy())
axs[3].imshow(x_cycled[idx].cpu().permute(1, 2, 0).detach().numpy())

for ax in axs:
    ax.axis("off")
plt.show()

# TODO WIP here

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-success"><h2>Checkpoint 3</h2>
# You've now learned the basics of what makes up a CycleGAN, and details on how to perform adversarial training.
# The same method can be used to create a CycleGAN with different basic elements.
# For example, you can change the archictecture of the generators, or of the discriminator to better fit your data in the future.
#
# You know the drill... let us know on the exercise chat!
# </div>

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# # Part 4: Evaluating the GAN

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
#
# ## That was fun!... let's load a pre-trained model
#
# Training the CycleGAN takes a lot longer than the few iterations that we did above. Since we don't have that kind of time, we are going to load a pre-trained model (for reference, this pre-trained model was trained for 7 days...).
#
# To continue, interrupt the kernel and continue with the next one, which will just use one of the pretrained CycleGAN models for the synapse dataset.

# %% editable=true slideshow={"slide_type": ""} tags=[]
from pathlib import Path
import torch

# TODO load the pre-trained model

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# Let's look at some examples. Can you pick up on the differences between original, the counter-factual, and the reconstruction?

# %% editable=true slideshow={"slide_type": ""} tags=[]
# TODO show some examples

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# We're going to apply the GAN to our test dataset.

# %% editable=true slideshow={"slide_type": ""} tags=[]
# TODO load the test dataset

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ## Evaluating the GAN
#
# The first thing to find out is whether the CycleGAN is successfully converting the images from one neurotransmitter to another.
# We will do this by running the classifier that we trained earlier on generated data.
#

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-info"><h3>Task 4.1 Get the classifier accuracy on CycleGAN outputs</h3>
#
# Using the saved images, we're going to figure out how good our CycleGAN is at generating images of a new class!
#
# The images (`real`, `reconstructed`, and `counterfactual`) are saved in the `test_images/` directory. Before you start the exercise, have a look at how this directory is organized.
#
# TODO
# - Use the `make_dataset` function to create a dataset for the three different image types that we saved above
#     - real
#     - reconstructed
#     - counterfactual
# </div>

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-banner alert-warning">
# We get the following accuracies:
#
# 1. `accuracy_real`: Accuracy of the classifier on the real images, just for the two classes used in the GAN
# 2. `accuracy_recon`: Accuracy of the classifier on the reconstruction.
# 3. `accuracy_counter`: Accuracy of the classifier on the counterfactual images.
#
# <h3>Questions</h3>
#
# - In a perfect world, what value would we expect for `accuracy_recon`? What do we compare it to and why is it higher/lower?
# - How well is it translating from one class to another? Do we expect `accuracy_counter` to be large or small? Do we want it to be large or small? Why?
#
# Let us know your insights on the exercise chat.
# </div>
# %%
# TODO make a loop on the data that creates the counterfactual images, given a set of options as input
counterfactuals, reconstructions, targets, labels = ...


# %% [markwodn]
# Evaluate the images
# %%
# TODO use the loaded classifier to evaluate the images
# Get the accuracies
def predict():
    # TODO return predictions, labels
    pass


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# We're going to look at the confusion matrices for the counterfactuals, and compare it to that of the real images.

# %%
print("The confusion matrix on the real images... for comparison")
# TODO Confusion matrix on the counterfactual images
confusion_matrix = ...
# TODO plot
# %%
print("The confusion matrix on the real images... for comparison")
# TODO Confusion matrix on the real images, for comparison
confusion_matrix = ...
# TODO plot

# %% [markdown]
# <div class="alert alert-banner alert-warning">
# <h3>Questions</h3>
#
# - What would you expect the confusion matrix for the counterfactuals to look like? Why?
# - Do the two directions of the CycleGAN work equally as well?
# - Can you think of anything that might have made it more difficult, or easier, to translate in a one direction vs the other?
#
# </div>

# %% [markdown]
# <div class="alert alert-block alert-success"><h2>Checkpoint 4</h2>
#  We have seen that our CycleGAN network has successfully translated some of the synapses from one class to the other, but there are clearly some things to look out for!
# Take the time to think about the questions above before moving on...
#
# This is the end of Section 4. Let us know on the exercise chat if you have reached this point!
# </div>

# %% [markdown]
# # Part 5: Highlighting Class-Relevant Differences

# %% [markdown]
# At this point we have:
# - A classifier that can differentiate between neurotransmitters from EM images of synapses
# - A vague idea of which parts of the images it thinks are important for this classification
# - A CycleGAN that is sometimes able to trick the classifier with barely perceptible changes
#
# What we don't know, is *how* the CycleGAN is modifying the images to change their class.
#
# To start to answer this question, we will use a [Discriminative Attribution from Counterfactuals](https://arxiv.org/abs/2109.13412) method to highlight differences between the "real" and "fake" images that are most important to change the decision of the classifier.

# %% [markdown]
# <div class="alert alert-block alert-info"><h3>Task 5.1 Get sucessfully converted samples</h3>
# The CycleGAN is able to convert some, but not all images into their target types.
# In order to observe and highlight useful differences, we want to observe our attribution method at work only on those examples of synapses:
# <ol>
#     <li> That were correctly classified originally</li>
#     <li>Whose counterfactuals were also correctly classified</li>
# </ol>
#
# TODO
# - Get a boolean description of the `real` samples that were correctly predicted
# - Get the target class for the `counterfactual` images (Hint: It isn't `cf_gt`!)
# - Get a boolean description of the `cf` samples that have the target class
# </div>

# %% editable=true slideshow={"slide_type": ""} tags=[]
####### Task 5.1 TODO #######

# Get the samples where the real is correct
correct_real = ...

# HINT GABA is class 1 and ACh is class 0
target = ...

# Get the samples where the counterfactual has reached the target
correct_cf = ...

# Successful conversions
success = np.where(np.logical_and(correct_real, correct_cf))[0]

# Create datasets with only the successes
cf_success_ds = Subset(ds_counterfactual, success)
real_success_ds = Subset(ds_real, success)


# %% editable=true slideshow={"slide_type": ""} tags=["solution"]
########################
# Solution to Task 5.1 #
########################

# Get the samples where the real is correct
correct_real = real_pred == real_gt

# HINT GABA is class 1 and ACh is class 0
target = 1 - real_gt

# Get the samples where the counterfactual has reached the target
correct_cf = cf_pred == target

# Successful conversions
success = np.where(np.logical_and(correct_real, correct_cf))[0]

# Create datasets with only the successes
cf_success_ds = Subset(ds_counterfactual, success)
real_success_ds = Subset(ds_real, success)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# To check that we have got it right, let us get the accuracy on the best 100 vs the worst 100 samples:

# %% editable=true slideshow={"slide_type": ""} tags=[]
model = model.to("cuda")

# %% editable=true slideshow={"slide_type": ""} tags=[]
real_true, real_pred = predict(real_success_ds, "Real")
cf_true, cf_pred = predict(cf_success_ds, "Counterfactuals")

print(
    "Accuracy of the classifier on successful real images",
    accuracy_score(real_true, real_pred),
)
print(
    "Accuracy of the classifier on successful counterfactual images",
    accuracy_score(cf_true, cf_pred),
)

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ### Creating hybrids from attributions
#
# Now that we have a set of successfully translated counterfactuals, we can use them as a baseline for our attribution.
# If you remember from earlier, `IntegratedGradients` does a interpolation between the model gradients at the baseline and the model gradients at the sample. Here, we're also going to be doing an interpolation between the baseline image and the sample image, creating a hybrid!
#
# To do this, we will take the sample image and mask out all of the pixels in the attribution. We will then replace these masked out pixels by the equivalent values in the counterfactual. So we'll have a hybrid image that is like the original everywhere except in the areas that matter for classification.

# %% editable=true slideshow={"slide_type": ""} tags=[]
dataloader_real = DataLoader(real_success_ds, batch_size=10)
dataloader_counter = DataLoader(cf_success_ds, batch_size=10)

# %% editable=true slideshow={"slide_type": ""} tags=[]
# %%time
with torch.no_grad():
    model.to(device)
    # Create an integrated gradients object.
    # integrated_gradients = IntegratedGradients(model)
    # Generated attributions on integrated gradients
    attributions = np.vstack(
        [
            integrated_gradients.attribute(
                real.to(device),
                target=target.to(device),
                baselines=counterfactual.to(device),
            )
            .cpu()
            .numpy()
            for (real, target), (counterfactual, _) in zip(
                dataloader_real, dataloader_counter
            )
        ]
    )

# %%

# %% editable=true slideshow={"slide_type": ""} tags=[]
# Functions for creating an interactive visualization of our attributions
model.cpu()

import matplotlib

cmap = matplotlib.cm.get_cmap("viridis")
colors = cmap([0, 255])


@torch.no_grad()
def get_classifications(image, counter, hybrid):
    model.eval()
    class_idx = [full_dataset.classes.index(c) for c in classes]
    tensor = torch.from_numpy(np.stack([image, counter, hybrid])).float()
    with torch.no_grad():
        logits = model(tensor)[:, class_idx]
        probs = torch.nn.Softmax(dim=1)(logits)
        pred, counter_pred, hybrid_pred = probs
    return pred.numpy(), counter_pred.numpy(), hybrid_pred.numpy()


def visualize_counterfactuals(idx, threshold=0.1):
    image = real_success_ds[idx][0].numpy()
    counter = cf_success_ds[idx][0].numpy()
    mask = get_mask(attributions[idx], threshold)
    hybrid = (1 - mask) * image + mask * counter
    nan_mask = copy.deepcopy(mask)
    nan_mask[nan_mask != 0] = 1
    nan_mask[nan_mask == 0] = np.nan
    # PLOT
    fig, axes = plt.subplot_mosaic(
        """
                                   mmm.ooo.ccc.hhh
                                   mmm.ooo.ccc.hhh
                                   mmm.ooo.ccc.hhh
                                   ....ggg.fff.ppp
                                   """,
        figsize=(20, 5),
    )
    # Original
    viz.visualize_image_attr(
        np.transpose(mask, (1, 2, 0)),
        np.transpose(image, (1, 2, 0)),
        method="blended_heat_map",
        sign="absolute_value",
        show_colorbar=True,
        title="Mask",
        use_pyplot=False,
        plt_fig_axis=(fig, axes["m"]),
    )
    # Original
    axes["o"].imshow(image.squeeze(), cmap="gray")
    axes["o"].set_title("Original", fontsize=24)
    # Counterfactual
    axes["c"].imshow(counter.squeeze(), cmap="gray")
    axes["c"].set_title("Counterfactual", fontsize=24)
    # Hybrid
    axes["h"].imshow(hybrid.squeeze(), cmap="gray")
    axes["h"].set_title("Hybrid", fontsize=24)
    # Mask
    pred, counter_pred, hybrid_pred = get_classifications(image, counter, hybrid)
    axes["g"].barh(classes, pred, color=colors)
    axes["f"].barh(classes, counter_pred, color=colors)
    axes["p"].barh(classes, hybrid_pred, color=colors)
    for ix in ["m", "o", "c", "h"]:
        axes[ix].axis("off")

    for ix in ["g", "f", "p"]:
        for tick in axes[ix].get_xticklabels():
            tick.set_rotation(90)
        axes[ix].set_xlim(0, 1)


# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-info"><h3>Task 5.2: Observing the effect of the changes on the classifier</h3>
# Below is a small widget to interact with the above analysis. As you change the `threshold`, see how the prediction of the hybrid changes.
# At what point does it swap over?
#
# If you want to see different samples, slide through the `idx`.
# </div>

# %% editable=true slideshow={"slide_type": ""} tags=[]
interact(visualize_counterfactuals, idx=(0, 99), threshold=(0.0, 1.0, 0.05))

# %% [markdown]
# HELP!!! Interactive (still!) doesn't work. No worries... uncomment the following cell and choose your index and threshold by typing them out.

# %% editable=true slideshow={"slide_type": ""} tags=[]
# Choose your own adventure
# idx = 0
# threshold = 0.1

# # Plotting :)
# visualize_counterfactuals(idx, threshold)

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-warning">
# <h4>Questions</h4>
#
# - Can you find features that define either of the two classes?
# -  How consistent are they across the samples?
# -  Is there a range of thresholds where most of the hybrids swap over to the target class? (If you want to see that area, try to change the range of thresholds in the slider by setting `threshold=(minimum_value, maximum_value, step_size)`
#
# Feel free to discuss your answers on the exercise chat!
# </div>

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# <div class="alert alert-block alert-success">
#     <h1>The End.</h1>
#     Go forth and train some GANs!
# </div>

# %% [markdown] editable=true slideshow={"slide_type": ""} tags=[]
# ## Going Further
#
# Here are some ideas for how to continue with this notebook:
#
# 1. Improve the classifier. This code uses a VGG network for the classification. On the synapse dataset, we will get a validation accuracy of around 80%. Try to see if you can improve the classifier accuracy.
#     * (easy) Data augmentation: The training code for the classifier is quite simple in this example. Enlarge the amount of available training data by adding augmentations (transpose and mirror the images, add noise, change the intensity, etc.).
#     * (easy) Network architecture: The VGG network has a few parameters that one can tune. Try a few to see what difference it makes.
#     * (easy) Inspect the classifier predictions: Take random samples from the test dataset and classify them. Show the images together with their predicted and actual labels.
#     * (medium) Other networks:  Try different architectures (e.g., a [ResNet](https://blog.paperspace.com/writing-resnet-from-scratch-in-pytorch/#resnet-from-scratch)) and see if the accuracy can be improved.
#
# 2. Explore the CycleGAN.
#     * (easy) The example code below shows how to translate between GABA and acetylcholine. Try different combinations. Can you start to see differences between some pairs of classes? Which are the ones where the differences are the most or the least obvious? Can you see any differences that aren't well described by the mask? How would you describe these?
#
# 3. Try on your own data!
#     * Have a look at how the synapse images are organized in `data/raw/synapses`. Copy the directory structure and use your own images. Depending on your data, you might have to adjust the image size (128x128 for the synapses) and number of channels in the VGG network and CycleGAN code.