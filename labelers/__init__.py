# labelers/ — one module per labeling method.
#
# Every labeler exposes the same entry point:
#
#     label(record) -> 0 | 1
#
# That uniformity is the point. The router picks a labeler by looking at
# evidence; the runner calls it without caring whether the answer came from a
# boolean expression or from a model. Adding a third method later means adding
# a file here, not rewriting the cascade.
