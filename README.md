# ML Compilers From Zero

**Course website: https://jsivark.github.io/ml-compilers-course/**

A free, self-paced path from intermediate Python and basic C to building your own machine-learning compiler, modelled on CMU 10-411 *Compilers for Machine Learning*. The website has all 41 modules with step-by-step instructions and portfolio projects. This repo holds the website's source and the compiler assignments with their tests.

## When the tests apply

**The automated tests start at Module 19.** Modules 0–18 (orientation, foundations and bridge) have no tests here. They use the labs, puzzle sets and test suites linked from each module page, such as the CS:APP labs, Tensor Puzzles and Nora Sandler's C compiler tests.

From Module 19 on, you build one compiler, and the tests in this repo check it. The test folders are numbered by the real course's weeks:

| Course module | Test folder | Tests | Run with |
|---|---|---|---|
| 19 | `tests/week01` | 66 | `python3 run_tests.py 1` |
| 20 | `tests/week02` | 57 | `python3 run_tests.py 2` |
| 21 | `tests/week03` | 60 | `python3 run_tests.py 3` |
| 22 | `tests/week04` | 54 | `python3 run_tests.py 4` |
| 23 | `tests/week05` | 60 | `python3 run_tests.py 5` |
| 24 | `tests/week06` | 63 | `python3 run_tests.py 6` |
| 25 | `tests/week07` | 41 | `python3 run_tests.py 7` |
| 26–29 | none | | graded by measured milestones (see each module page) |

Every test in Modules 19–25 has been checked against a reference implementation that follows the rules below, including the places marked *(convention)*. The tests cover normal programs, edge cases an obvious-but-wrong compiler gets wrong, and `rejected_`, `mismatch_` and `overbudget_` variants.

```
run_tests.py        run a week's tests against ./compile (or any command)
tests/weekNN/       .uir test programs; the filename prefix gives the expected outcome
curriculum/         the course content (one JSON file per part)
site/               the website generator; python3 site/build.py writes docs/
tools/              content and link checker
```

## The contract

Build one program, `./compile`, in any language. Everything here runs on macOS and Linux; on Windows, use WSL2. It takes `.uir` files and prints one line for each file:

```
$ ./compile tests/week01/add_fold.uir tests/week01/rejected_assert_dtype_mismatch.uir
MATCH tests/week01/add_fold.uir
REJECTED tests/week01/rejected_assert_dtype_mismatch.uir
```

The expected outcome comes from the filename prefix:

| Prefix | Expected outcome |
|---|---|
| (none) | `MATCH` |
| `mismatch_` | `MISMATCH` |
| `rejected_` | `REJECTED` (invalid before it runs) |
| `overbudget_` | `OVERBUDGET` |

To check your compiler, run `python3 run_tests.py 1` (or 2, 3, …). The number is the test folder (the course week), not the module number: Module 19 is `1`. Every week must also keep passing all earlier weeks' tests.

*(convention)* Each test is judged by the rules of its own week, and `run_tests.py` sets the environment variable `UIR_WEEK` to that week. Later weeks only add features, so this matters for exactly one test: ALU ops on vectors are an error in Week 1 (`week01/rejected_alu_on_vector.uir`) and valid from Week 4. Read `UIR_WEEK` (default: the latest week you support) to tell the two apart.

**Rules, the same as the real course.** No BLAS/cuBLAS, PyTorch, Triton, MLIR or tinygrad inside your compiler. You can use clang, LLVM, the CUDA driver/runtime APIs and cuda-python. Don't let an AI write the compiler for you. Use it to explain things, to debug, and to write tests.

**Write tests too.** Each week, add at least 10 tests of your own. Good tests are cases where an obvious-but-wrong compiler would fail. Make sure each one has a single, clearly correct answer by working it out by hand.

**Where the conventions come from.** The format follows the public 10-411 Week 1 spec and the example programs on 10-411.com. Where the public material says nothing, this edition picks a convention. The places where it does that are marked *(convention)* below. The real course may differ.

---

## Week 1 (course wk 18): UOps, rewrites, bounds

**Format.** Each line is a binding, `%name = op src... key=val...`. A literal like `3` or `true` is a constant. `[a b c]` is `stack a b c`. `#` starts a comment.

**Types and shapes.**
- Dtypes are `i32` and `bool`.
- Shapes are rank 0, or rank 1 for stacks. ALU ops take scalars only.
- `i32` arithmetic wraps on overflow.

**Hash-consing.** Every `(op, src, arg)` triple is exactly one node. `%a = add 2 4` and `%b = add 2 4` are the same node.

**Ops.**
- Constants and stacks: `const` (written as a literal), `stack` / `[...]`, `index v i`.
- Lambda calculus: `param [] [lo hi]? slot=k dtype=t addrspace=ALU` and `call body arg0 arg1 ...`.
- ALU ops: `cast dtype=t`, `add`, `mul`, `max`, `div` (floor; −1 when dividing by 0), `mod` (floor; x when dividing by 0), `xor`, `shl` (shift amount taken mod 32), `cmplt`, `where`.
- `assert x expected` ends every file. Its expected value must be a literal or a stack of literals.

**Bounds.** Compute an interval `[lo, hi]` for every node: constants are exact, params use their declared limits, and ALU ops use interval arithmetic. If an overflow is possible, the interval widens to the full i32 range. An `index` is REJECTED unless its bounds *prove* it is in range, across all calls. A call is REJECTED if an argument's bounds fall outside the param's limits.

**Cost.** Each node is charged once (hash-consing makes repeats free). Elementwise ops cost the number of result elements. `[]` and `index` cost 1. `const`, `param` and `assert` cost 0. A call costs 1 + C(body), so calling the same body twice charges it twice.

**Budgets.**
- File larger than 4096 bytes: OVERBUDGET.
- After parsing, 100 or more distinct nodes, or 300 or more source edges: OVERBUDGET.
- Static cost of 1,000,000 or more: OVERBUDGET.
- *(convention)* These budgets stay in force for every week's tests, with the cost rules extended in each week below. Turn them off (for example with a flag) when you run your own big programs such as `gemm_256.uir` or MNIST.

Hash-consing shows up in the budgets: `hashcons_node_budget.uir` has 120 bindings of the same `add 2 4` (one node, not 120), and in `hashcons_cost_shared_call.uir` an expensive call written twice is charged once.

**Build it in this order.**
1. Tokenizer and parser.
2. `UOp(op, src, arg)` with interning, so equality is identity.
3. Lazily cached `dtype`, `shape`, `bounds` and `cost`.
4. A validator.
5. An evaluator that runs the graph.
6. A pattern-rewrite engine (`UPat` + `PatternMatcher` + `graph_rewrite` to a fixed point) with constant folding and the identities x+0, x\*1, x\*0, x^x, max(x,x), where(true,a,b). Prove it works by folding every MATCH test down to `assert c c`.

**Reading.** tinygrad's `tinygrad/uop/ops.py` (the UOp, UPat, PatternMatcher and graph_rewrite classes) and its tests in `test/null/test_pattern_matcher.py` and `test/null/test_uop_vmin_vmax.py`. Read them after your own attempt.

**Done when:** `python3 run_tests.py 1` passes 66/66, and you've written 10 or more tests of your own.

## Week 2 (course wk 19): loads, stores, memory; render C

**New ops.**
- `extern shape slot=k dtype=t`: a global buffer.
- `store dst value`.
- `load buf`.
- `after buf effect...`: buf, but only once the listed effects have happened.
- `index buf i` on a buffer gives an addressable element.
- Nested `(op ...)` expressions are now allowed anywhere an operand can go.

**Shapes and values.**
- The shape operand of `extern` is an integer `n` (shape `(n,)`), a list `[2 3]`, or `[]` for a scalar. Every dimension must be at least 1 *(convention)*.
- Buffers start zero-filled *(convention)*. Two different buffers may not share a slot *(convention)*. Identical `extern` lines are one node, so one buffer.
- `extern`, `index` of a buffer and `after` are buffer (GLOBAL) values. ALU ops, `reduce` and movement ops need ALU values: `load` the buffer first. `store dst v` needs a buffer `dst` and an ALU value `v` of the same dtype and shape (no implicit casts), and yields an effect. `after`'s extra operands must be effects (Week 3 also allows ranges), and there must be at least one.
- `assert` of a buffer value compares the buffer's contents (as in the official Week 3 example) *(convention)*.

**Ordering rules.** "Ordered" means one node is reachable from the other through operands.
- A `load` must be ordered with every store to that buffer, even a store to a different element *(convention: otherwise REJECTED)*. So a load that should see a store goes through `after`, and a load that must happen *before* a later store has to feed that store's value. Reading an old version that a later, unrelated store overwrites is REJECTED, not a stale read.
- Two stores to the same buffer must be ordered unless their index bounds are disjoint on some axis *(convention)*. A store to the whole buffer overlaps everything.
- Stores and loads must be provably in range, just as indexing is in Week 1.
- With these rules any topological order gives the same answer.

**Cost** *(convention)*. `load` and `store` cost the number of elements moved. `extern`, `after` cost 0. `index` costs 1, as in Week 1. A shape literal such as `[2 3]` is a stack and costs its elements.

**Renderer.** Starting this week, *execute by generating C*:
1. Topologically sort the graph.
2. Emit one C function with no loops.
3. Compile it with `clang -O2 -shared`.
4. Call it through `ctypes` (or dlopen), with the buffers you allocated.

Keep your Week 1 interpreter as a second backend and cross-check the two.

**Reading.** Russ Cox, *Hardware Memory Models*; tinygrad's `renderer/cstyle.py`.

**Done when:** tests/week02 and all earlier weeks pass, through the C backend.

## Week 3 (course wk 20): loops, floats, runtime; matmul and conv

**New ops.**
- `range n slot=k`: a loop variable over 0..n-1, with bounds [0, n−1]. `n` is an integer literal of at least 1 *(convention)*. Different ranges must use different slots *(convention)*; the same `range` line written twice is one node and can drive two separate loops.
- `end effect range...`: closes loops, innermost first. The effect must be a store, end or call, and every listed range must still be open in it *(convention)*. A range that reaches the `assert` without being closed is REJECTED.
- `recip x`, for f32 only. `recip 0.0` is infinity.
- Dtype `f32`. Float literals contain a `.`, like `0.5`, `-2.0` or `3.0e38` *(convention: digits, `.`, digits, optional exponent)*. A literal outside the f32 range is REJECTED. `div`, `mod`, `shl` and `xor` stay integer-only.

**Loop semantics** *(convention)*. A node runs once per iteration of exactly the ranges it depends on, and is hoisted out of the others. That is the README's "place each computation in the innermost loop it depends on". So a `load %acc` that doesn't depend on `%i` is read once, before the loop. To re-read a buffer every iteration (an accumulator), write `load (after %acc %i)`: a range in `after` makes the buffer depend on it. Iterations run in order, outermost range last in the `end` list, so the order of an `end`'s ranges can change the result.

**Floats** *(convention)*.
- Every f32 op rounds to f32 (IEEE round-to-nearest-even). Don't let clang fuse multiply-adds: compile with `-ffp-contract=off`.
- `cast` f32→i32 truncates toward zero, i32→f32 rounds to nearest, and f32→bool is `x != 0`.
- An f32 `assert` is exact after rounding the expected literal to f32. So `assert (add 0.1 0.2) 0.3` matches in f32. Expected f32 values must be written with a `.`: `assert (recip 2.0) 0` is a dtype mismatch.

**Cost** *(convention)*. A node's cost is multiplied by the trip counts of the ranges it depends on. `range` and `end` cost 0.

**What to build.**
- Render ranges as C `for` loops, and place each computation in the innermost loop it depends on.
- Write matmul (M=N=K=256) and a 3×3 conv2d as UIR files by hand. Check them against NumPy to within 1e-4.

**Reading.** Goldberg on floating point. CS231n conv notes (im2col).

**Done when:** the week03 tests pass, plus your hand-written `gemm_256.uir` and `conv3x3.uir`.

## Week 4 (course wk 21): rangeify, reduce, materialization

**New ops.**
- `expand x n`: broadcast a scalar to shape (n,), with n ≥ 1.
- `reduce x op=add|max pop=n`: reduce the last n axes *(convention)*. `pop` is required, with 1 ≤ n ≤ rank. On bool, both `add` and `max` act as "any". An f32 `add` sums in index order, left to right *(convention)*, so `reduce [16777216.0 1.0 1.0]` is `16777216.0`. Bounds: `max` keeps the input's bounds, and `add` multiplies them by the number of elements reduced.
- ALU ops now accept rank-1 inputs. All operands must have exactly the same shape: there is no implicit broadcasting, so `add [1 2] 1` is REJECTED *(convention)*. Use `expand`.
- Cost *(convention)*: an elementwise op costs its elements, `reduce` costs its input's elements, and `expand` costs 0.

**The core pass, *rangeify*.** Rewrite every shaped op into scalar code over explicit ranges, then decide what gets **materialized**:
- Fuse elementwise chains into a single loop.
- Stage a temporary buffer only where needed, for example the input of a reduce that is read twice.

**Reading.** The Halide paper (separating the algorithm from the schedule); the tinygrad-notes posts on scheduling and fusion.

**Done when:**
- The week04 tests pass.
- `reduce(mul(a,b))` compiles to one fused loop with no temporary buffer. Check the generated C.

## Week 5 (course wk 22): movement ops

**New ops.**
- `reshape x [shape]`. The element counts must match. `[]` is the scalar shape.
- `permute x [order]`. The order must be a permutation of 0..rank−1. `p = permute x order` has `p.shape[k] = x.shape[order[k]]`.
- `pad x [[before after] ...]`, padding with zeros (false for bool) *(convention)*. There is one pair per axis, and each amount is ≥ 0. A padded value's bounds include 0.
- `shrink x [[start end] ...]`, keeping `start ≤ i < end`, with `0 ≤ start < end ≤ dim` *(convention: half-open and non-empty)*.
- `expand x [shape]`: same rank, each axis equal or 1 → any size. A scalar can expand to any shape *(convention)*.
- Shapes of any rank. No dimension may be 0 *(convention)*.
- The shape and order operands are literal lists. Movement ops take ALU values (load a buffer first) and cost 0 *(convention)*.

**What to build.**
- Movement ops never copy. Each one becomes index arithmetic, plus a validity mask for pad.
- Simplify the resulting `div`/`mod` index expressions using your Week 1 bounds.
- Matmul is now just `reshape → expand → mul → reduce`.

**Reading.** ezyang, *PyTorch internals*; tinygrad-notes, ShapeTracker; Tensor-Puzzles (do all of them).

**Done when:** the week05 tests pass, and conv2d written only with movement ops plus mul/reduce matches NumPy.

## Week 6 (course wk 23): autodiff, real models

**New syntax and ops.**
- `{ ... }` lexical scopes, whose value is the last binding. A scope can stand anywhere a value can. Names bound inside are invisible after the `}`. Rebinding a name that is visible from outside is REJECTED *(convention)*, as is an empty scope. Unused inner bindings are unreachable nodes, as in Week 1.
- `extern ... url=path`, which loads a file-backed buffer. *(convention)* The path is relative to the `.uir` file. The file holds raw little-endian elements (4 bytes for f32 and i32, 1 byte for bool), and its size must match the shape exactly. A missing file is REJECTED.
- `gradient loss wrt`: d loss / d wrt, with wrt's shape. *(convention)*
  - `loss` must be an f32 scalar and `wrt` an f32 value.
  - Every node between them must be pure (ALU, movement, `reduce`, `stack`, `index` of a value, `cast`, `where`). A path through `load`, `store`, `after`, `range`, `call` or another `gradient` is REJECTED.
  - Gradients flow only through f32 nodes, so a cast to i32 stops them. If loss doesn't depend on wrt, the result is zeros.
  - Ties in `max` and in `reduce op=max` split the gradient evenly.
  - Hash-consing applies: `wrt` is a node, so every use of that node counts.
  - A `gradient` costs the cost of its loss again.
- Transcendental ops: `exp2`, `log2`, `sqrt`, `sin`, for f32 only, implemented yourself, for example with range reduction plus a polynomial. *(convention)* An f32 assert whose actual side uses any of them compares within `1e-5 + 1e-5·|expected|`. All other f32 asserts stay exact.

**Milestones.** These are the real 10-411 Week 6 goals:
1. `gradient` as a graph rewrite, with a rule per op. Test it against finite differences on 20 random graphs.
2. Train an MNIST MLP to **at least 97%** test accuracy in under 5 minutes on CPU.
3. Run a small LLM (the TinyStories model behind Karpathy's llama2.c, `stories15M`) and produce the same tokens as `run.c`.
4. Run ResNet-18 inference on one image, with the top-1 class matching PyTorch's output (computed outside your compiler).

**Reading.** Autodidax; the Baydin AD survey, §3.

## Week 7 (course wk 24): CPU memory hierarchy, threads

**New syntax.** `range ... axis=GLOBAL|LOOP|UPCAST`. A `call` of a kernel launches it.

*(convention)*
- `axis` is a scheduling hint and doesn't change results. It defaults to `LOOP`, and any other value (including lowercase, or `LOCAL`, which is Week 8) is REJECTED.
- A kernel is a body whose value is an effect (an `end` or a `store`), with all of its ranges closed. `call kernel args...` runs it and is itself an effect, so use it in `after` and `end`, never as a value. Args fill `param` slots exactly as in Week 1, including the limit checks, so index bounds inside the kernel use the params' limits.
- `(call %k)` written twice is one node, so the kernel runs once.
- A call counts as a store to every buffer its body stores to. Loads and other stores of those buffers must be ordered with the call, and two calls that store the same buffer must be ordered with each other. Two calls of one kernel with different args can never be ordered, so they are REJECTED if the kernel stores.
- Cost: a call costs 1 plus its body's cost, as in Week 1.

**What to build.**
- Tiling, loop reordering, unrolling (UPCAST), SIMD-friendly code (vector types or `#pragma clang loop vectorize`), and multithreading over GLOBAL axes with pthreads.

**Targets.**
- 1024³ f32 matmul at **50% or more of single-socket peak**. Report GFLOPS.
- Conv and reduce within 3× of NumPy.

**Reading.** siboehm, *Fast Multidimensional Matrix Multiplication on CPU*; salykova, matmul-cpu; how-to-optimize-gemm; Algorithmica.

## Week 8 (course wk 25): GPU backend

**What to build.**
- A CUDA renderer: GLOBAL/LOCAL axes map to the grid and blocks, plus shared memory (`addrspace=LOCAL`) and `barrier`.
- Compile with NVRTC through cuda-python.
- Every earlier test must pass on the GPU.

**Target.** Elementwise and reduce ops at **70% or more of memory bandwidth**, measured with Nsight Compute.

**Reading.** CUDA Programming Guide ch. 1–5; GPU-Puzzles; Stanford CS149 GPU lectures.

## Week 9 (course wk 26): tensor cores, fast GEMM, flash attention

**What to build.**
- Register tiling, vectorized loads, double buffering, and `mma.sync` tensor-core instructions emitted by your compiler (not hand-written CUDA).
- A fused attention kernel.

**Targets.**
- fp16 4096³ GEMM at **70% or more of cuBLAS** (benchmark cuBLAS separately, with PyTorch, outside your compiler).
- Flash-attention forward pass at 60% or more of PyTorch SDPA.

**Reading.** siboehm, CUDA matmul worklog; spatters, *mma matmul*; FlashAttention 1 and 2; flash-attention-minimal; ThunderKittens.

## Week 10 (course wk 27): multiple GPUs, sharding

**What to build.**
- A `shard` annotation on buffers.
- A pass that inserts all-reduce and all-gather.
- Data-parallel MNIST training on 2 or more GPUs (NCCL through ctypes is allowed).
- Tensor-parallel matmul.

**Reading.** *How to Scale Your Model*; *Ultra-Scale Playbook*; LLM-Training-Puzzles.

## Week 11 (course wk 28): SOTA inference and training

**What to build.**
- KV cache, batching, int8 weights and speculative decoding for the Week 6 LLM.
- Report tokens/sec against llama2.c and gpt-fast.

**Also due:** a one-page final project proposal covering the goal, baseline, metric and plan.

## Weeks 12–14 (course wk 29–31): final project

See the ideas list on the course site. Deliver code, a benchmark harness, and a 4-page report.

## License

Content: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code: MIT. Reuse, remix and teach from it freely, including commercially. Just credit **jsivark — ml-compilers-course** with a link back. Linked third-party material keeps its own license. The UIR format, operation semantics and test-file naming convention come from the public [CMU 10-411 Week 1 handout](https://10-411.com/assignments/week1.pdf); the test cases in `tests/` were written for this project. See [LICENSE](LICENSE).
