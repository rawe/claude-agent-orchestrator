---
title: Implement what i want
description: Explores, plan and implement a wish or an idea
---

## Goal

Implment a given command or a implemention file.


## Variables

Read from the following input:
<input>
$ARGUMENTS
</input>


Extract out of the input the following variables:
<implementation_task> - A description of what needs to be implemented.
<doc_working_directory> - The document working directory where all docs will be created
<sanatized_task_name> - A sanitized version of the implementation task name suitable for file and directory names.

**Important:** If the doc working directory is not provided use the following default value: ./docs/<sanatized_task_name>/


## Steps

### Recap
Use a subagent to recap the given implmenation task and try to understand the intent and the actual requirement behind it.

-> Write this task recap in the file: <doc_working_directory>/task_recap.md


### Exploration

Use the explore subagent to the current codebase and project context to understand what needs to be done to implement the given task.
Goal of exploration is to find relevant files, modules, components and their locations which could be useful for the implementation of the given task with a breif description of why they are relevant.

* Input for the explore agent:
  - A highlevel instruction of the goal of the exploration.
  - The file ref for task recap from <doc_working_directory>/task_recap.md
  - The path to the output directory where the exploration result should be written to.
* Output from the explore agent:
  - Writes the exploration result to the given output directory.
  - summary of the exploration result.

-> Ensure this exploration result is written to the file: <doc_working_directory>/exploration_result.md - Do not read it.

### Planning
Use the plan subagent to create a concrete plan for implementing the given task. the plan agent should get 
* Input for the plan agent:
  - The file ref to the task recap from <doc_working_directory>/task_recap.md
  - The file ref to the exploration result from <doc_working_directory>/exploration_result.md
  - The path to the output directory where the plan should be written to.
* Output from the plan agent:
  - A step by step plan for implementing the given task as a markdown file including checklist of steps to be done.
  - summary of the plan - in brief
  - potential questions to the user before starting the implementation.

*Hints for the plan agent*
* Focus on creating a concrete plan to handover to the main agent. - create one concise plan file.

-> Ensure this plan file is written to the file: <doc_working_directory>/implementation_plan.md - Do not read it.


### Implementation
* Ask the user potential questions from the plan summary before starting the implementation.
* After answering and user approval start the implementation of the given task using the implementation plan from <doc_working_directory>/implementation_plan.md