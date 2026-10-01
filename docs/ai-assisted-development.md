# AI-Assisted Development

This project was built with help from AI coding tools. I am documenting that
openly because using assistance responsibly is part of the engineering work.

## How AI Helped

AI was used as a pair-programming and review tool for tasks such as:

- discussing RAG architecture and retrieval tradeoffs;
- explaining unfamiliar APIs and machine-learning concepts;
- suggesting test cases and edge cases;
- drafting and improving documentation;
- reviewing code for readability, typing, and error handling;
- troubleshooting local development and tooling problems.

## What I Was Responsible For

I remained responsible for:

- defining the project scope and choosing German federal law as the domain;
- deciding which suggestions matched the project goals;
- reading and adapting generated code instead of accepting it blindly;
- running tests, type checks, builds, and live API checks;
- building and evaluating the local retrieval index;
- checking claims against actual output and recorded metrics;
- documenting limitations instead of presenting the project as production-ready.

## Verification Process

AI-generated suggestions were treated as untrusted until verified. The project
uses the following checks:

```bash
make verify
```

This runs pytest, Ruff, mypy, the TypeScript compiler, and the frontend build.
Retrieval changes can also be measured against the checked-in golden set with:

```bash
make eval
```

## What I Can Explain Without AI

I should be able to explain and defend the main design choices in this project:

- why legal-heading chunking fits the domain;
- why BM25 and dense retrieval are complementary;
- why reciprocal rank fusion is used instead of combining raw scores;
- what a cross-encoder reranker adds and costs;
- what hit rate and mean reciprocal rank measure;
- what citation validation prevents and what it does not prevent;
- which parts still need work before production use.

If I cannot explain a change, it should not be merged until I understand it.
