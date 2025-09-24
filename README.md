# WebGen-R1: Incentivizing LLMs to Generate Functional and Aesthetic Websites with Reinforcement Learning

<p align="center" width="100%">
<img src="assets/WebGen-R1.jpg" alt="WebGen-R1" style="width: 90%; min-width: 100px; display: block; margin: auto;">
</p>

## Installation

> [!CAUTION]
> The libraries require **CUDA 12.4**. If you encounter segmentation fault errors, verify your CUDA version by running `nvcc --version`.

### 1. Open-R1 Environment Setup
```shell
conda create -n webgen-r1 python=3.11
conda activate webgen-r1
pip install --upgrade pip 
pip install vllm==0.8.5.post1 
pip install setuptools  
pip install flash-attn --no-build-isolation 
pip install tensorboard 

GIT_LFS_SKIP_SMUDGE=1 pip install -e ".[dev]" 
pip install selenium==4.15.2 
pip install pillow==10.3.0 
```
This process will also install **PyTorch v2.6.0**, which is **critical** because the vLLM binaries are built for this specific version.  
Next, log into your Hugging Face and Weights & Biases accounts:

```shell
huggingface-cli login # Required for pushing datasets and models to the HF Hub
wandb login # Enables experiment tracking during training
sudo apt-get install git-lfs
git-lfs --version
```

### 2. Web Rendering Environment
```shell
# Install nvm (Node Version Manager) and Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
node --version  
npm --version
nvm --version
npm install -g pm2
npm install -g vite
```

### 3. Install Google Chrome and ChromeDriver
1. Download **Chrome for Testing** and **ChromeDriver** from: https://googlechromelabs.github.io/chrome-for-testing/

```bash
wget https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chrome-linux64.zip
wget https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chromedriver-linux64.zip
```

2. Unzip and grant execution permissions:  
`chmod +x ./chrome-linux64/chrome`  
`chmod +x ./chromedriver-linux64/chromedriver`

3. Run the following commands to check for potential issues:

```bash
# 1. Install required libraries for ChromeDriver if you encounter `/lib64/libnss3.so: version \`NSS_3.30' not found` errors
/path_to_chromedriver-linux64/chromedriver --version 
yum install -y nss libXcb libX11 libXcomposite libXcursor libXdamage libXext libXfixes libXi libXrandr libXrender libXtst cups-libs libXScrnSaver alsa-lib

# 2. Install required libraries for Chrome if you get errors like:
# `./chrome-linux64/chrome: error while loading shared libraries: libatk-bridge-2.0.so.0: cannot open shared object file: No such file or directory`
/path_to_chrome-linux64/chrome --version 
yum install -y at-spi2-atk libxkbcommon at-spi2-core dbus-libs gtk3 nss alsa-lib libdrm libXcomposite libXcursor libXdamage libXext libXfixes libXi libXrandr libXScrnSaver libXtst pango cups-libs libffi
```

## Data Preparation

The parquet dataset is stored in the `./web/data/parquet` directory.  
If you encounter data loading errors, convert the original dataset from `jsonl` format (available at `https://github.com/mnluzimu/WebGen-Bench/tree/main/data`) to `parquet` format by running:

```bash
cd ./web/data
python jsonl_to_parquet.py
```

## Model Training

```bash
bash runs/sft.sh
bash runs/train.sh
```