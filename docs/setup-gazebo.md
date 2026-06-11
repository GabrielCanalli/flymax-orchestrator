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
