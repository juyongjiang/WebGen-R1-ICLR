# WebGen-R1: Incentivizing LLMs to Generate Functional and Aesthetic Websites with Reinforcement Learning

## Installation

> [!CAUTION]
> Libraries rely on CUDA 12.4. If you see errors related to segmentation faults, double check the version your system is running with `nvcc --version`.

### 1. Open-R1 Envs
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
This will also install PyTorch `v2.6.0` and it is **very important** to use this version since the vLLM binaries are compiled for it. 
Next, log into your Hugging Face and Weights and Biases accounts as follows:

```shell
huggingface-cli login # for dataset and model pushing to HF hub 
wandb login # for training tracking
sudo apt-get install git-lfs
git-lfs --version
```

### 2. Web Render Envs
```shell
# download nvm (node version manager) Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
node --version  
npm --version
nvm --version
npm install -g pm2
npm install -g vite
```

### 3. Install Google Chrome and Driver
1. Download Chrome for Testing and ChromeDriver at https://googlechromelabs.github.io/chrome-for-testing/;

```bash
wget https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chrome-linux64.zip
wget https://storage.googleapis.com/chrome-for-testing-public/138.0.7204.94/linux64/chromedriver-linux64.zip
```

2. Unzip and assign execution: `chmod +x ./chrome-linux64/chrome`, `chmod +x ./chromedriver-linux64/chromedriver`

3. Please run the following commands to check if there is something wrong. 

```bash
# 1. install libs for chromedriver if you meet the errors of `/lib64/libnss3.so: version `NSS_3.30' not found`
/path_to_chromedriver-linux64/chromedriver --version 
yum install -y nss libXcb libX11 libXcomposite libXcursor libXdamage libXext libXfixes libXi libXrandr libXrender libXtst cups-libs libXScrnSaver alsa-lib

# 2. install libs for chrome if you have the errors of `./chrome-linux64/chrome: error while loading shared libraries: libatk-bridge-2.0.so.0: cannot open shared object file: No such file or directory`
/path_to_chrome-linux64/chrome --version 
yum install -y     at-spi2-atk     libxkbcommon     at-spi2-core     dbus-libs     gtk3     nss     alsa-lib     libdrm     libXcomposite     libXcursor     libXdamage     libXext     libXfixes     libXi     libXrandr     libXScrnSaver     libXtst     pango     cups-libs     libffi
```

## Data Preparation

The parquet dataset is located in `./web/data/parquet` folder, if you meet the errors of data loading, please run the following command to transfer the original `jsonl` format data (`https://github.com/mnluzimu/WebGen-Bench/tree/main/data`) to `parquet` format.

```bash
cd ./web/data
python jsonl_to_parquet.py
```


## Model Training

```bash
bash runs/sft.sh
bash runs/train.sh
```