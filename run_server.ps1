cd S:\Solomon
. .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH          = 'S:\Solomon\src'
$env:RWKV_MODEL_PATH     = 'S:\Solomon\models\rwkv\RWKV-x060-World-3B-v2.1-20240417-ctx4096.pth'
$env:RWKV_TOKENIZER_PATH = 'S:\Solomon\models\rwkv\20B_tokenizer.json'

$LOG = 'S:\Solomon\server.log'
"--- $(Get-Date) starting uvicorn ---" | Out-File -Encoding utf8 -FilePath $LOG -Append

python -m uvicorn src.bridge.main:app --host 127.0.0.1 --port 8765 --workers 1 --log-level debug 2>&1 |
  Tee-Object -FilePath $LOG -Append

Write-Host "Uvicorn exited with code $LASTEXITCODE"
Read-Host 'Press Enter to close this window'
