param(
    [Parameter(Mandatory=$true)][string]$InputJson,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$pilotData = Get-Content -LiteralPath $InputJson -Raw -Encoding UTF8 | ConvertFrom-Json
$pilotSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $pilotVoices = @($pilotSynth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'fr-FR' })
    if ($pilotVoices.Count -eq 0) {
        @{status='unavailable'; provider='System.Speech local'; reason='No local fr-FR voice'} |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputDirectory 'manifest.json') -Encoding UTF8
        return
    }
    $pilotVoice = $pilotVoices | Where-Object { $_.VoiceInfo.Name -eq 'Microsoft Julie' } | Select-Object -First 1
    if (-not $pilotVoice) { $pilotVoice = $pilotVoices[0] }
    $pilotSynth.SelectVoice($pilotVoice.VoiceInfo.Name)
    $pilotSynth.Rate = 0
    $pilotFiles = @()
    foreach ($pilotScene in $pilotData.scenes) {
        if (-not $pilotScene.narration) { $pilotFiles += $null; continue }
        $pilotHashInput = $pilotVoice.VoiceInfo.Name + '|rate=0|' + $pilotScene.narration
        $pilotHasher = [System.Security.Cryptography.SHA256]::Create()
        try { $pilotHash = [BitConverter]::ToString($pilotHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($pilotHashInput))).Replace('-', '').ToLower() }
        finally { $pilotHasher.Dispose() }
        $pilotPath = Join-Path $OutputDirectory ($pilotHash + '.wav')
        if (-not (Test-Path -LiteralPath $pilotPath)) {
            $pilotSynth.SetOutputToWaveFile($pilotPath)
            $pilotSynth.Speak([string]$pilotScene.narration)
            $pilotSynth.SetOutputToNull()
        }
        $pilotFiles += [string]$pilotPath
    }
    @{status='generated'; provider='System.Speech local'; voice=$pilotVoice.VoiceInfo.Name; rate=0; files=$pilotFiles} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'manifest.json') -Encoding UTF8
}
finally { $pilotSynth.Dispose() }
