# Contributing

This is primarily a learning and portfolio project, but small improvements and
bug reports are welcome.

## Local Setup

Follow the setup instructions in the main README, then run:

```bash
make verify
```

## Making a Change

1. Keep changes focused and easy to review.
2. Add or update tests when behavior changes.
3. Run `make verify` before opening a pull request.
4. If retrieval behavior changes, run `make eval` and explain any metric change.
5. Do not commit raw law data, processed chunks, model weights, or secrets.

## Pull Request Notes

Please describe:

- what changed;
- why the change is useful;
- how it was tested;
- any limitations or follow-up work.
