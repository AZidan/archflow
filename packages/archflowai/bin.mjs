#!/usr/bin/env node
// `archflowai` is the domain spelling of `archflow`. Same CLI, same arguments: this
// resolves the real package (a dependency, so npx always fetches its latest) and runs it.
import { createRequire } from "node:module";
await import(createRequire(import.meta.url).resolve("archflow/scripts/archflow.mjs"));
