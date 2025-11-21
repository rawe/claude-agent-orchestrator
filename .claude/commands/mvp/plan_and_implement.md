---
description: Plan and implement a Minimum Viable Product (MVP) for a project.
argument-hint: [implementation_block_file]
---

## Goal
Plan and implment the given implementation block file.


## Inputs
- <implmentation_block_file> - The path to the implementation block file that describes the implementation block: $1


## Steps
1. Read <implmentation_block_file> to understand the implementation block description.
2. use the plan subagent to plan the implmentation and reading all referenced files and create an implmenation check list next to the <implmentation_block_file> named `XX-IMPLEMENTATION-CHECKLIST.md` where `XX` is the same number as in the <implmentation_block_file>. This checklist should contain all the steps needed to implement the given implementation block. Each step should be clear and concise, and should include any necessary details or instructions for completing the step.
The checklist is called <implementation_checklist_file>.

**IMPORTANT:** CHECKLIST DETAILS:
The <implmentation_block_file> must contain:
* references to all the files needed for the implementation
* clear instraction at the beginning what the overall goal is
*  containg the instruction that each checkpoint should be marked as done when completed

3. Ask the user whether to proceed with the implementation of the block using the AskUserQuestion tool or to change the plan or to do it for the next block, if there is one.
4. If the user agrees to proceed, implement the steps in the checklist one by one.


