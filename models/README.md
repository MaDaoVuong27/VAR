# models — model weights / checkpoints

Nơi lưu chung các model đã tải về hoặc fine-tune (self-host, ràng buộc ≤ 9B params — xem `docs/TASK_SPEC.md`). Dùng chung giữa các experiment thay vì mỗi experiment tự giữ 1 bản copy.

```
models/
└── <tên-model>/
    ├── ... (weights — gitignored, xem .gitignore ở gốc repo)
    └── SOURCE.md    # link tải gốc (HF repo/commit) + cách tải lại, vì weight không commit vào git
```

Weight thật sự (`*.safetensors`, `*.bin`, `*.gguf`) đã bị gitignore ở mức repo — chỉ commit `SOURCE.md`/config nhỏ để người khác (hoặc BTC khi review source code) biết cách tải lại đúng model.

Mọi model dùng trong `src/` phải được liệt kê trong [`../docs/CONFIG_REFERENCE.md`](../docs/CONFIG_REFERENCE.md), trỏ tới đúng subfolder ở đây.

_(chưa có model nào)_
