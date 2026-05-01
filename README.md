```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	routing(routing)
	parser(parser)
	intent(intent)
	personalization(personalization)
	draft(draft)
	tone(tone)
	review(review)
	__end__([<p>__end__</p>]):::last
	__start__ --> routing;
	draft --> tone;
	intent --> personalization;
	parser --> intent;
	personalization --> draft;
	review -.-> __end__;
	review -.-> draft;
	routing -.-> __end__;
	routing -.-> parser;
	tone --> review;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```