# cs-from-scratch
[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsco1%2Fcs-from-scratch%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=FFD43B)](https://github.com/sco1/cs-from-scratch/blob/main/pyproject.toml)
[![GitHub License](https://img.shields.io/github/license/sco1/cs-from-scratch?color=magenta)](https://github.com/sco1/cs-from-scratch/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/cs-from-scratch/main.svg)](https://results.pre-commit.ci/latest/github/sco1/cs-from-scratch/main)

Following along with David Kopec's [*Computer Science From Scratch*](https://nostarch.com/computer-science-from-scratch).

The original source code for the text can be found in its [GitHub repository](https://github.com/davecom/ComputerScienceFromScratch).

# Differences From Text
Initial implementations of each chapter's content will adhere as much as possible to the book's implementation, including inline and end-of-chapter exercises. Once the book's implementation is complete, I may occasionally indulge my own curiosity and expand on the concepts introduced.

Significant differences in my implementations from the text are noted below.

## All Chapters
* Each chapter is responsible for its own CLI and given a project-wide entry point rather than invoking via `python -m ...`
  * Chapter 1: `brainfuck`
  * Chapter 2: `NanoBASIC`
  * Chapter 3: `RetroDither`
  * Chapter 4: `Impressionist`
  * Chapter 5: `Chip8`
  * Chapter 6: `NESEmulator`
* Unit & integration testing is written using `pytest` rather than `unittest`. Additional tests maybe be included to maximize feasible coverage for each chapter.

## Chapter 1
* The `Brainfuck` interpreter class is initialized using a source string rather than a file path
  * Use the `Brainfuck.from_file` method to load a source file
* The number of cells available to the interpreter can be optionally specified
* The `?>` prefix is used when prompting for input
* In addition to specifying a Brainfuck source file, a source string can also be passed to the CLI, e.g. `brainfuck -s ",>,[<.>-]"`

## Chapter 2
* A `--dump_ast` CLI option is provided to write the AST to a `<filename>_AST.txt` file in the same directory as the loaded source file
