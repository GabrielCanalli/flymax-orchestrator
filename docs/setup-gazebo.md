# Setup: Ubuntu 24.04 + Gazebo Harmonic + PX4 SITL

This guide provides a step-by-step walkthrough for installing **PX4 SITL** and **Gazebo Harmonic** on **Ubuntu 24.04** and testing the simulation backend integration. 

No prior ROS 2 experience is required to follow these instructions.

---

## Prerequisites

Before starting, ensure your Ubuntu 24.04 system is fully updated. Open a terminal and run:

```bash
sudo apt update && sudo apt upgrade -y
```

Install the core utilities required for the setup:

```bash
sudo apt install -y git curl gnupg lsb-release python3-pip
```

---

## Installation Steps

### 1. Install Gazebo Harmonic
We will use the official Open Source Robotics Foundation (OSRF) repository to install Gazebo Harmonic on Ubuntu 24.04.

```bash
# Add the OSRF official GPG key
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs.osrfoundation.org-keyring.gpg

# Add the stable Gazebo repository to your system sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs.osrfoundation.org-keyring.gpg   $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null

# Update package lists and install Gazebo Harmonic
sudo apt update
sudo apt install -y gz-harmonic
```

### 2. Clone and Configure PX4 Autopilot
​Next, clone the official PX4 repository recursively to include all necessary submodules, and run the automated setup script for Ubuntu.

```bash
# Clone the PX4 Autopilot repository with its submodules
git clone [https://github.com/PX4/PX4-Autopilot.git](https://github.com/PX4/PX4-Autopilot.git) --recursive

# Navigate into the repository directory
cd PX4-Autopilot

# Run the Ubuntu setup script to install additional compilers and simulation dependencies
bash ./Tools/setup/ubuntu.sh
```