#!/bin/bash

# Define variables
CONDA_INSTALLER_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
CONDA_INSTALLER="Miniconda3-latest-Linux-x86_64.sh"
CONDA_PATH="$HOME/miniconda3"
ENV_NAME="myenv_9"
PYTHON_VERSION="3.9"
PROJECT_DIR="$(pwd)"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

# Step 1: Install Miniconda if not already installed
if [ ! -d "$CONDA_PATH" ]; then
    echo "Downloading Miniconda..."
    wget -q $CONDA_INSTALLER_URL -O $CONDA_INSTALLER
    chmod +x $CONDA_INSTALLER

    echo "Installing Miniconda..."
    bash $CONDA_INSTALLER -b -p $CONDA_PATH
    rm $CONDA_INSTALLER
else
    echo "Miniconda already installed at $CONDA_PATH."
fi

# Step 2: Initialize Conda if not already initialized
if ! grep -q "conda initialize" ~/.bashrc; then
    echo "Initializing Conda..."
    eval "$($CONDA_PATH/bin/conda shell.bash hook)"
    $CONDA_PATH/bin/conda init bash
    source ~/.bashrc
else
    echo "Conda is already initialized in .bashrc."
    eval "$($CONDA_PATH/bin/conda shell.bash hook)"
fi

# Step 3: Verify Conda installation
if ! command -v conda &> /dev/null; then
    echo "Conda command not found. Please check the installation."
    exit 1
else
    echo "Conda installation verified. Version:"
    conda --version
fi

# Step 4: Create Conda Environment with Python 3.9
echo "Creating environment '$ENV_NAME' with Python $PYTHON_VERSION..."
conda create --name $ENV_NAME python=$PYTHON_VERSION -y

# Step 5: Activate Conda environment
echo "Activating environment '$ENV_NAME'..."
source activate $ENV_NAME

# Step 6: Install packages from requirements.txt if it exists
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing packages from $REQUIREMENTS_FILE..."
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "Requirements file not found. Skipping package installation."
fi



# Step 7.: Run FiLM scripts as specified
echo "Running FiLM scripts..."
bash ./script/ILI_script/FiLM/FiLM.sh
bash ./script/Exchange_script/FiLM/FiLM.sh

echo "Scripts execution completed."
