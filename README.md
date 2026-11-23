# ML Compilers From Zero

**Course website: https://jsivark.github.io/ml-compilers-course/**

A free, self-paced path from intermediate Python and basic C to building your own machine-learning compiler, modelled on CMU 10-411 *Compilers for Machine Learning*. The website has all 40 modules with step-by-step instructions and portfolio projects. This repo holds the website's source and the compiler assignments with their tests.

## When the tests apply

**The automated tests start at Module 18.** Modules 0–17 (orientation, foundations and bridge) have no tests here. They use the labs, puzzle sets and test suites linked from each module page, such as the CS:APP labs, Tensor Puzzles and Nora Sandler's C compiler tests.

From Module 18 on, you build one compiler, and the tests in this repo check it. The test folders are numbered by the real course's weeks:

| Course module | Test folder | Run with |
|---|---|---|
| 18 | `tests/week01` | `python3 run_tests.py 1` |
| 19 | `tests/week02` | `python3 run_tests.py 2` |
| 20 | `tests/week03` | `python3 run_tests.py 3` |
| 21 | `tests/week04` | `python3 run_tests.py 4` |
| 22 | `tests/week05` | `python3 run_tests.py 5` |
| 23 | `tests/week06` | `python3 run_tests.py 6` |
| 24 | `tests/week07` | `python3 run_tests.py 7` |
| 25–28 | none | graded by measured milestones (see each module page) |

Module 18 has a full suite of 65 tests, checked against a reference implementation. Modules 19–24 have starter sets whose answers were worked out by hand. See the [About page](https://jsivark.github.io/ml-compilers-course/about.html) for what has and hasn't been checked.

```
run_tests.py        run a week's tests against ./compile (or any command)
tests/weekNN/       .uir test programs; the filename prefix gives the expected outcome
curriculum/         the course content (one JSON file per part)
site/               the website generator; python3 site/build.py writes docs/
tools/              content and link checker
```

## The contract

Build one program, `./compile`, in any language. It takes `.uir` files and prints one line for each file:

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

To check your compiler, run `python3 run_tests.py 1` (or 2, 3, …). The number is the test folder (the course week), not the module number: Module 18 is `1`. Every week must also keep passing all earlier weeks' tests.

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

**Build it in this order.**
1. Tokenizer and parser.
2. `UOp(op, src, arg)` with interning, so equality is identity.
3. Lazily cached `dtype`, `shape`, `bounds` and `cost`.
4. A validator.
5. An evaluator that runs the graph.
6. A pattern-rewrite engine (`UPat` + `PatternMatcher` + `graph_rewrite` to a fixed point) with constant folding and the identities x+0, x\*1, x\*0, x^x, max(x,x), where(true,a,b). Prove it works by folding every MATCH test down to `assert c c`.

**Reading.** tinygrad's `tinygrad/uop/ops.py` (the UOp, UPat, PatternMatcher and graph_rewrite classes) and its tests in `test/null/test_pattern_matcher.py` and `test/null/test_uop_vmin_vmax.py`. Read them after your own attempt.

**Done when:** `python3 run_tests.py 1` passes 65/65, and you've written 10 or more tests of your own.

## Week 2 (course wk 19): loads, stores, memory; render C

**New ops.**
- `extern shape slot=k dtype=t`: a global buffer.
- `store dst value`.
- `load buf`.
- `after buf effect...`: buf, but only once the listed effects have happened.
- `index buf i` on a buffer gives an addressable element.
- Nested `(op ...)` expressions are now allowed anywhere an operand can go.

**Ordering rules.**
- A `load` must be ordered by `after` relative to every store to that buffer *(convention: an unordered load is REJECTED)*.
- Stores must be provably in range, just as indexing is in Week 1.

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
- `range n slot=k`: a loop variable over 0..n-1, with bounds [0, n−1].
- `end effect range...`: closes loops, innermost first.
- `recip x`, for f32 only.
- Dtype `f32`. Float literals contain a `.`.

**What to build.**
- Render ranges as C `for` loops, and place each computation in the innermost loop it depends on.
- Write matmul (M=N=K=256) and a 3×3 conv2d as UIR files by hand. Check them against NumPy to within 1e-4.

**Reading.** Goldberg on floating point. CS231n conv notes (im2col).

**Done when:** the week03 tests pass, plus your hand-written `gemm_256.uir` and `conv3x3.uir`.

## Week 4 (course wk 21): rangeify, reduce, materialization

**New ops.**
- `expand x n`: broadcast a scalar to shape (n,).
- `reduce x op=add|max pop=n`: reduce the last n axes *(convention)*.
- ALU ops now accept rank-1 inputs.

**The core pass, *rangeify*.** Rewrite every shaped op into scalar code over explicit ranges, then decide what gets **materialized**:
- Fuse elementwise chains into a single loop.
- Stage a temporary buffer only where needed, for example the input of a reduce that is read twice.

**Reading.** The Halide paper (separating the algorithm from the schedule); the tinygrad-notes posts on scheduling and fusion.

**Done when:**
- The week04 tests pass.
- `reduce(mul(a,b))` compiles to one fused loop with no temporary buffer. Check the generated C.

## Week 5 (course wk 22): movement ops

**New ops.**
- `reshape x [shape]`.
- `permute x [order]`.
- `pad x [[before after] ...]`, padding with zeros *(convention)*.
- `shrink x [[start end] ...]`.
- `expand x [shape]`.
- Shapes of any rank.

**What to build.**
- Movement ops never copy. Each one becomes index arithmetic, plus a validity mask for pad.
- Simplify the resulting `div`/`mod` index expressions using your Week 1 bounds.
- Matmul is now just `reshape → expand → mul → reduce`.

**Reading.** ezyang, *PyTorch internals*; tinygrad-notes, ShapeTracker; Tensor-Puzzles (do all of them).

**Done when:** the week05 tests pass, and conv2d written only with movement ops plus mul/reduce matches NumPy.

## Week 6 (course wk 23): autodiff, real models

**New syntax and ops.**
- `{ ... }` lexical scopes, whose value is the last binding.
- `extern ... url=path`, which loads a file-backed buffer.
- `gradient loss wrt`.
- Transcendental ops: `exp2`, `log2`, `sqrt`, `sin`, implemented yourself, for example with range reduction plus a polynomial.

**Milestones.** These are the real 10-411 Week 6 goals:
1. `gradient` as a graph rewrite, with a rule per op. Test it against finite differences on 20 random graphs.
2. Train an MNIST MLP to **at least 97%** test accuracy in under 5 minutes on CPU.
3. Run a small LLM (the TinyStories model behind Karpathy's llama2.c, `stories15M`) and produce the same tokens as `run.c`.
4. Run ResNet-18 inference on one image, with the top-1 class matching PyTorch's output (computed outside your compiler).

**Reading.** Autodidax; the Baydin AD survey, §3.

## Week 7 (course wk 24): CPU memory hierarchy, threads

**New syntax.** `range ... axis=GLOBAL|LOOP|UPCAST`. A `call` of a kernel launches it.

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
