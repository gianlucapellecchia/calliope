## Comments

The config includes several keys that are optional, e.g. `objective` &
`objective_options`, or `spore_options`.  For the most general case to
work, all child keys should be marked `optional` or have a `default`
(see `spore_options`).

The rules for technology, nodes, and links are different.  They cannot
be nested, and they are not a static set.  Based on the attributes
that are present in the config, the appropriate entries from the rules
file are picked.

Note that validation steps that involve reading datasets from files,
should not be done as part of the config validation.  The config
validation should only check if the file is present, if it's the right
kind (CSV, NetCDF, etc).  Reading the dataset should be done
separately, so as not to repeat it, and do it efficiently (for example
partial reads).

Base technologies that should be defined by calliope core (`demand`,
`supply`, `transmission`, etc), they are in `typedconfig/conf/`.
These should be merged with the user provided technology definitions.
The user provided technology definitions can inherit from the built-in
technologies by specifying them in the `parent` key (they can also
refer to other user defined technologies).  Note that only a built-in
technology can be at the base of the inheritance tree.

## Rules

- `run.yaml` & `model.yaml` are for the respective sections in the
  main config
- `techs.yaml`, `nodes.yaml`, & `links.yaml` are to define
  technologies, nodes, and links respectively.
- `time_masks.yaml`: these are WIP rules for time masks and time
  aggregations, which can be applied at a later stage (multi-stage
  validation)

## Code snippet

A snippet like the one below could be used to dump out existing
defaults/configs to something that can be easily copy pasted into
rules files.

```
allowed_constraints = glom(
    conf,
    (
        T.items(),
        Iter({"t": "0", "c": "1.allowed_constraints"}).map(T.values()).all(),
        dict,
    ),
)

res = defaultdict(set)
for k, v in allowed_constraints.items():
    for _v in v:
        res[_v].add(k)

for k, v in res.items():
    res[k] = list(sorted(v))

```
