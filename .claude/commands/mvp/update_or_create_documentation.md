---
description: Update or create docuemtnation for the project.


## Goal:
Creation of a proper mostly redundant free documentation using progressive disclosure.

## Input
The user provided you context you need to be aware of when cerateing the proper documentation.

<context>
$ARGUTMENTS
</context>

## Documentation structure we are aiming for:

* a concise readme.md that gives an overview of the project, its purpose, and how to get started.
* if the reame gets to big and handles too much details, we need to create a docs/ directory for more in-depth documentation.
* in the docs directory we create separate markdown files for different aspects of the project
* examples for these files could be:
  * architecture.md: detailing the system architecture and design decisions.
  * setup.md: providing step-by-step instructions for setting up the development environment.
  * usage.md: explaining how to use the project, including examples and common use cases.
  * configuration.md: outlining configuration options and how to customize the project. (this can also be split up in environment-variables.md and config-files.md, what is suitbale for the project)
* If you identify the need for additional documentation files based on the project context ASK the user before creating them.


## Progressive Disclosure Strategy:
1. Start with a high-level overview in the readme.md.
2. Identify sections that require more detail and create separate markdown files in the docs/ directory.
3. Reference the detailed docs from the readme.md to guide users to more information as needed. Be explicite and concise when the user should read a specific document for more details.


# Important Notes:
* Avoid redundancy: Ensure that information is not duplicated across multiple documents. Each piece of information should have a single source of truth.
* Clarity and conciseness: Write clear and concise documentation, don't be verbose.
* BUT: give a proper and brief introduction to each topic before going into details in the docs/ files.

