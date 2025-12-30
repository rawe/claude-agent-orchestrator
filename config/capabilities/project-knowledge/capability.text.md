## Knowledge Graph Schema

### Entities

#### Module
- module_name: complete name of the module
- module_key: short key (e.g. M001, may contain leading zeros)
- summary: concise description

#### ConfluencePage
- title: page title
- url: page URL
- summary: concise description
- page_id: concrete page ID

#### AdoTicket
- title: ticket title
- url: ticket URL
- summary: concise description
- ticket_number: concrete ticket number

### Relationship

#### is_related (Module → ConfluencePage | AdoTicket)
- link_type: ConfluencePage | AdoTicket
- reason: brief explanation why the module is linked

Multiple relations to the same or different targets are allowed. Reasons may be merged if relations are superseded.