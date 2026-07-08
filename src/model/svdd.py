"""
DeepSVDD implementasi PyTorch murni (tanpa pyod/numba).

Prinsip DeepSVDD (Ruff et al., 2018):
  Latih sebuah jaringan f untuk memetakan data normal sedekat mungkin ke
  satu titik pusat c (hypersphere center). Skor anomali = jarak kuadrat
  representasi ke pusat: makin jauh = makin anomali.

Dipakai di atas embedding LogBERT (CLS). Modul ini menjadi satu-satunya
sumber definisi jaringan agar training (notebook) dan inference (predict.py)
selalu konsisten.
"""
import numpy as np
import torch
import torch.nn as nn

REP_DIM = 64


class DeepSVDDNet(nn.Module):
    """Encoder ringkas tanpa bias (sesuai anjuran DeepSVDD agar tak kolaps trivial)."""

    def __init__(self, in_dim: int, rep_dim: int = REP_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 128, bias=False),
            nn.ReLU(),
            nn.Linear(128, rep_dim, bias=False),
        )

    def forward(self, x):
        return self.net(x)


def train_svdd(X: np.ndarray, epochs: int = 30, device: str = "cpu",
               rep_dim: int = REP_DIM):
    """
    Latih DeepSVDD pada embedding normal.

    Returns:
        net    : jaringan terlatih (eval mode)
        center : tensor pusat hypersphere (CPU)
        scores : jarak kuadrat tiap sampel training ke pusat (np.ndarray)
    """
    Xt = torch.as_tensor(X, dtype=torch.float32, device=device)
    net = DeepSVDDNet(Xt.shape[1], rep_dim).to(device)

    # Inisialisasi pusat c = rata-rata representasi awal (hindari nilai ~0)
    with torch.no_grad():
        c = net(Xt).mean(0)
        c[c.abs() < 1e-6] = 1e-6

    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    net.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss = ((net(Xt) - c) ** 2).sum(1).mean()
        loss.backward()
        opt.step()

    net.eval()
    with torch.no_grad():
        scores = ((net(Xt) - c) ** 2).sum(1).cpu().numpy()
    return net, c.detach().cpu(), scores


def anomaly_scores(net: DeepSVDDNet, center: torch.Tensor,
                   X: np.ndarray, device: str = "cpu") -> np.ndarray:
    """Hitung skor anomali (jarak kuadrat ke pusat) untuk embedding baru."""
    Xt = torch.as_tensor(X, dtype=torch.float32, device=device)
    with torch.no_grad():
        return ((net(Xt) - center.to(device)) ** 2).sum(1).cpu().numpy()
