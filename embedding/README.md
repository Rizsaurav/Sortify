clone Qwen-8B to your repo via 

# Make sure git-lfs is installed (https://git-lfs.com)
git lfs install

git clone https://huggingface.co/Qwen/Qwen3-Embedding-8B

# If you want to clone without large files - just their pointers
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Qwen/Qwen3-Embedding-8B
