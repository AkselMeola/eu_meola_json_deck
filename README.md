# Stream controller plugin: Json Deck

**Work in progress**

Interpret a simple JSON protocol from URLs, command outputs or local files to display buttons.

## Why ?
Once you implement the protocol, then you can develop your action in any programming language you like.








## The protocol

```json
{
	"frame_duration": 5,
	"frames": [
		{
			"top_label": "Foo",
			"center_label": "Bar",
			"bottom_label": "99",
			"media_path": "/"
		},
		{
			"top_label": "Foo 1",
			"center_label": "Bar 1",
			"bottom_label": "77",
			"media_path": "/"
		}

	]
}
```

// TODO: More description and examples


## TODO: 

 - [ ] Documentation - usage examples
 - [ ] Implement button action payload - command, browser, refresh
 - [ ] Add option to always re-download image
 - [ ] Pack in some pre-rendered gauges for easy use. E.g. use prefix: asset:/path/to/asset.png 
 - [ ] Implement a background color change using `set_background_color()`