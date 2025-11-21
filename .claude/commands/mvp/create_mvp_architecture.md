---
description: Create a minimal viable product (MVP) architecture from a given architecture file.
argument-hint: ["architecture_file"]
---

## Goal
Create a minimal viable product (MVP) architecture file from a given architecture file.

## Inputs
- <architecture_file> - The path to the architecture file that describes the full architecture: $1

## Outputs
- <mvp_architecture_file> - The path to the generated MVP architecture file. using <architecture_file> but having the suffix `_mvp` before the file extension.

## Steps

1. Read <architecture_file> to understand the full architecture description.
2. understand technology it uses to achieve the goal
3. Think what could be simplified for an mvp but does not block us in the future to enhance the mvp later, ask the user for each simplicity using the AskUserQuestion tool
  **IMPORTANT:** involve the user for each decision and give the rational for the suggestion, also sometimes more then one option is
  possible, explain in brief the impact, do it for each recommandation step by step
4. Write down an new document <mvp_architecture_file> that mimics the first one but contains the more mvp styled version using the decisions made in step 3.
