# Final Project 2023

**Static Analysis of Financial Apps on Android**  
Detecting Data Collection and Protection Practices

Author: Feiyang Xue

Email: feiyang.xue.2022@bristol.ac.uk



## Requirements

- Python 3.10
- JDK 17
- CUDA (Nvidia GPU)

## Prepare environment

1. Install OpenJDK 17
2. Install MiniConda / Anaconda
3. Install CUDA (or you can use cudatoolkit provided by conda)
4. Create a new conda environment using `conda env create -f environment.yml`

## Description

- API-Permission_Mapping/  
  API-Permission mapping table, ContentProvider permission mapping table and other basic information extraction Python project
- AndroidPlatformTools/  
  Android source code parsing tool Kotlin project for the previous tool
- APKAnalysis/
  Text analysis tools and report generation tools Python project
- APKAnalysisTools/  
  APK decompilation and information extraction tool Kotlin project
- APKCrawler/  
  APK crawler Python project
