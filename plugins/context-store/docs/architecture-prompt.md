Please see my implementation of the python commands in the skill agent orchestrator and the observability. There was a pattern where this python command called an endpoint in the
  observability pattern. This was good to enhance my Agent Orchestration Framework with observability. Now I want a new enhancement. At the moment decoupled from the Agent
  Orchestration Framework. So it is a new one. But the pattern remains the same. I want to have a skill in a separate plugin which I want to use to retrieve documents and push
  documents to a server. This should be provided as a skill with Python using UV. So the interface should be very simple, that I can have this command line with a push and a pull
  command with a given file and maybe an identifier. Or how the identifier is handled is up to you, because maybe the identifier is given after a push. And I need a query command for
  querying for documents and getting document IDs back. So three commands. And then I need a server implementation separate from the skill. Needs to be started as a server. That
  should also be implemented in Python. And this handles all the files in a proprietary file system or directory format, which is abstracted from the interface. And that can be very,
  very simple at the beginning. I want you to think of a strategy or an architecture which would go with it. Please make a suggestion for an architecture which Python commands I
  need, which I use in the skill so that an I-coding system can easily use it. And the other part, the server part, which actually provides the endpoints for the pull, push endpoint,
  and of course, a query endpoint to get what is in there.