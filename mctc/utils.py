# AUTOGENERATED! DO NOT EDIT! File to edit: notebooks/00_utils.ipynb (unless otherwise specified).

__all__ = ['to_np', 'zero_grad', 'float64', 'compare_fwd_bwd', 'timed', 'benchmark_fwd_bwd', 'report',
           'load_cupy_module']

# Cell
import torch
import numpy as np

# Cell
def to_np(x):
    return x.clone().detach().cpu().numpy()

def zero_grad(*xs):
    return [x.grad.zero_() for x in xs if hasattr(x, 'grad') and x.grad is not None]

def float64(func):
    return lambda *args: func(*[x.to(torch.float64) if hasattr(x, 'dtype') and x.dtype is torch.float else x for x in args])

def compare_fwd_bwd(impl_A, impl_B, inputs, *args):
    fwds, bwds = [], []
    for impl in (impl_A, impl_B):
        fwd = impl(inputs, *args)
        fwd.backward()
        fwds.append(to_np(fwd))
        bwds.append(to_np(inputs.grad))
        zero_grad(inputs)
    print(f'fwd diff: {np.max(np.abs(fwds[0]-fwds[1])):.2e}')
    print(f'bwd diff: {np.max(np.abs(bwds[0]-bwds[1])):.2e}')
    return fwds, bwds

# Cell
def timed(func, *inputs):
    start, end = [torch.cuda.Event(enable_timing=True) for _ in range(2)]
    start.record(); output = func(*inputs); end.record()
    torch.cuda.synchronize()
    return output, start.elapsed_time(end)

def benchmark_fwd_bwd(fwd_impl, *inputs, warmup=5, nloops=20):
    def fwd_bwd_times(fwd_impl, *inputs):
        output, fwd_time = timed(fwd_impl, *inputs)
        _, bwd_time = timed(output.backward)
        zero_grad(*inputs)
        return (fwd_time, bwd_time)
    [fwd_bwd_times(fwd_impl, *inputs) for _ in range(warmup)]
    fwd_times, bwd_times = map(np.array, zip(*[fwd_bwd_times(fwd_impl, *inputs) for _ in range(nloops)]))
    return {'fwd': fwd_times, 'bwd': bwd_times, 'tot': fwd_times+bwd_times}

def report(times):
    for k,v in times.items():
        print(f'{k}: {v.mean():.2f}ms ({v.min():.2f}-{v.max():.2f}ms)')

# Cell
def load_cupy_module(fname, **kwargs):
    import cupy as cp
    with open(fname) as f:
        code = f.read()
    macros = [f'#define {k} {v}' for k,v in kwargs.items()]
    code = '\n'.join(macros + [code])
    return cp.RawModule(code=code)