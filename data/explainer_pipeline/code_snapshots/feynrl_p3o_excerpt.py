"""Auditable excerpt from FeynRL P3O.

Source: https://github.com/FeynRL/FeynRL
Revision: dfe85351e28a3744ab0eb02d2299fc1e6d3d5752
Original path: algs/P3O/p3o.py, lines 107-135 and 192-223.
This snapshot is documentation input, not imported runtime code.
"""

def calculate_ess(valid_ratios):
    sum_w = valid_ratios.sum()
    sum_w_2 = valid_ratios.pow(2).sum()
    total = valid_ratios.numel()
    ess = (sum_w**2) / (sum_w_2 + 1e-8) / total
    return float(ess)


def p3o_terms(logprobs, old_logprobs, advantages, mask, kl_behavioral):
    logratio = logprobs - old_logprobs
    ratio = logratio.exp()
    ess_factor = calculate_ess(ratio[mask])
    rho = ratio.clamp(min=0, max=ess_factor)
    policy = -(rho.detach() * logprobs * advantages * mask).sum()
    trust_region = (1 - ess_factor) * kl_behavioral
    return policy + trust_region
