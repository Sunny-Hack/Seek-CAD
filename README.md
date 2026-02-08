
[![ICLR 2026](https://img.shields.io/badge/ICLR-2026-blue.svg)](https://iclr.cc/)
# Seek-CAD : A Self-refined Generative Modeling for 3D Parametric CAD Using Local Inference via DeepSeek (ICLR 2026)

<p align="center">
  <img src="assets/framework.png" width="100%" alt="Seek-CAD Framework">
</p>

## Dataset 

<p align="center">
  <img src="assets/SSR_Design_Paradigm.png" width="100%" alt="Seek-CAD Framework">
</p>

### 🧩 Pre-processed Text-SSR Pairs

We provide 4 pre-processed `.txt` files containing over **23K** Text2SSR (Sketch, Sketchbased feature, and Refinements) pairs. You can access these files by unzipping the archive located at `Dataset/preprocessed_txt2ssr`.

- **Total Samples**: 23,313 pairs.
- **File Format**: `.txt` (Text-SSR pairs).

**File Breakdown:**

- `Text2SSR_part1.txt`: **5,199** samples
- `Text2SSR_part2.txt`: **6,825** samples
- `Text2SSR_part3.txt`: **6,275** samples
- `Text2SSR_part4.txt`: **5,014** samples
  
**Sample Format:**

Each sample within these files consists of a **Description** paired with its corresponding **SSR Code**.

**Example:**

<p align="center">
  <img src="assets/text2ssr_samples.png" width="800" alt="RAG Corpus Sample Visualization">
</p>

## Citation

If you find this useful for your research, please cite our paper:

```bibtex
@inproceedings{li2026seekcad,
  title={Seek-CAD: A Self-refined Generative Modeling for 3D Parametric CAD Using Local Inference via DeepSeek},
  author={Li, Xueyang and [Add Co-authors Here]},
  booktitle={International Conference on Learning Representations (ICLR)},
  year={2026},
  url={[https://openreview.net/forum?id=xxxxx](https://openreview.net/forum?id=xxxxx)}  % (可选：如果你有OpenReview链接建议贴在这里)
}
