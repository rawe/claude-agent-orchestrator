---
title: Implement what i want
description: Explores, plan and implement a wish or an idea
---

## Goal

Implement what the user wants by given specifications or a specification files.

## Variables

Read from the following input:
<input>
$ARGUMENTS
</input>


Extract out of the input the following variables:
<implementation_task> - A description of what needs to be implemented.
<doc_working_directory> - The document working directory where all docs will be created
<sanatized_task_name> - A sanitized version of the implementation task name suitable for file and directory names.

**Important:** If the doc working directory is not provided use the following default value: ./tickets/<sanatized_task_name>/


## Steps

### 1. Recap
Use a subagent to recap the given implmenation task and try to understand the intent and the actual requirement behind it.
-> Write this task recap in the file: <doc_working_directory>/01_task_recap.md

**IMPORTANT:** Ask the user if further exploration of the code base or web research is needed, give a suggestion based on the task recap.
-> if not, skip the exploration specific step.


### 2. Exploration

### 2a Exploration in Codebase

Use the explore subagent to the current codebase and project context to understand what needs to be done to implement the given task.
Goal of exploration is to find relevant files, modules, components and their locations which could be useful for the implementation of the given task with a breif description of why they are relevant.

* Input for the explore agent:
  - A highlevel instruction of the goal of the exploration.
  - The file ref for task recap from <doc_working_directory>/01_task_recap.md
  - The path to the output directory where the exploration result should be written to.
* Output from the explore agent:
  - Writes the exploration result to the given output directory.
  - summary of the exploration result.

**Hints for the explore agent**
* Focus on finding relevant parts of the codebase which are related to the given task.
* the result file should consist json list of relevant files with their paths and a brief description of why they are relevant. (properties: file_path, description)

-> Ensure this exploration result is written to the file: <doc_working_directory>/02a_exploration_codebase_result.md - Do not read it.

### 2b Exploration through WebSearch

If the user requested external exploration (web research) or if the exploration in codebase was not sufficient, use the websearch subagent to explore external resources like documentation, libraries, frameworks or other relevant resources to understand what needs to be done to implement the given task.
* Input for the websearch agent:
  - A highlevel instruction of the goal of the exploration.
  - The file ref for task recap from <doc_working_directory>/01_task_recap.md
  - The path to the output directory where the exploration result should be written to.
* Output from the websearch agent:
  - Writes the exploration result to the given output directory.
  - summary of the exploration result.

**Hints for the webresearch agent**
* Focus on finding relevant parts of the codebase which are related to the given task.
* the result file should consist json list of relevant webpages with their urls and a brief description of why they are relevant. (properties: url, description)

-> Ensure this exploration result is written to the file: <doc_working_directory>/02b_exploration_websearch_result.md - Do not read it.

### 3. Planning
Use the plan subagent to create a concrete plan for implementing the given task. the plan agent should get 
* Input for the plan agent:
  - The file ref to the task recap from <doc_working_directory>/01_task_recap.md
  - The file ref to the exploration result from <doc_working_directory>/02a_exploration_codebase_result.md (if available)
  - The file ref to the exploration result from <doc_working_directory>/02b_exploration_websearch_result.md (if available)
  - The path to the output directory where the plan should be written to.
* Output from the plan agent:
  - A step by step plan for implementing the given task as a markdown file including checklist of steps to be done.
  - summary of the plan - in brief
  - potential questions to the user before starting the implementation.

*Hints for the plan agent*
* Focus on creating a concrete plan to handover to the main agent. - create one concise plan file.

-> Ensure this plan file is written to the file: <doc_working_directory>/03_implementation_plan.md - Do not read it.


### Implementation
* Ask the user potential questions from the plan summary before starting the implementation.
* After answering and user approval start the implementation of the given task using the implementation plan from <doc_working_directory>/03_implementation_plan.md