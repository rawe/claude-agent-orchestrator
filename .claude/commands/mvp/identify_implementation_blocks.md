---
description: Identify implementation blocks for the product architecture.
argument-hint: ["architecture_file"]
---

## Goal
Identify and outline the key implementation blocks required to build the product based on the provided architecture file.

## Inputs
- <architecture_file> - The path to the architecture file that describes the product architecture: $1

## Outputs
- multiple files: using the <architecture_file> but created in the subfolder `implementation` having the naming pattern `XX-TOPIC` before the file extension, where `XX` is a sequential number starting from 01 and `TOPIC` is a sanatized name of the implementation block.
  - Placeholder for the first document: <implementation_blocks_plan_1>
  - Placeholder for the second document: <implementation_blocks_plan_2>
  - Placeholder for the third document: <implementation_blocks_plan_3>
  ...
  - Placeholder for the nth document: <implementation_blocks_plan_n>

## Steps
1. Read <architecture_file> to understand the product architecture description.

2. Break the minimal viable product architecture file down into feasible sub-tasks that can be done in one session, giving a good step towards our end goal. not too small but not too big. So each section or each milestone should have one benefit. of the order you would approach it. Think of that you create now number documents starting with 01_ and naming it properly. What needs to be done? Each plan should reference the relevant sections out of the MVP file. So the MVP file itself should also be referenced. But it must be dedicated point to the important facts. It should not be a really detailed one. It should only, the first step is pointing out big blocks. Think of implementation sessions here in Cloud Code. How would we approach it? What structure would you have in there? Ask me for that. And then afterwards create these blocks. I'm interested in the granularity you decide to go with.


IMPORTANT: The <architecture_file> must be referenced with a relative path in the created documents. 