"""Auditable pseudocode excerpt from the official RoFormer README.

Source: https://github.com/ZhuiyiTechnology/roformer
Revision: dfc678ad506fc527ba17ead8db23cbe4d947a9b4
Original path: README.md, lines 18-32.
This snapshot is documentation input, not imported runtime code.
"""

cos_pos = repeat_elements(sinusoidal_pos[..., None, 1::2], rep=2, axis=-1)
sin_pos = repeat_elements(sinusoidal_pos[..., None, ::2], rep=2, axis=-1)
qw2 = stack([-qw[..., 1::2], qw[..., ::2]], 4)
qw2 = reshape(qw2, shape(qw))
qw = qw * cos_pos + qw2 * sin_pos
kw2 = stack([-kw[..., 1::2], kw[..., ::2]], 4)
kw2 = reshape(kw2, shape(kw))
kw = kw * cos_pos + kw2 * sin_pos

# Attention after rotating query and key.
a = einsum("bjhd,bkhd->bhjk", qw, kw)
