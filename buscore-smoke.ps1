Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Base = "http://127.0.0.1:8765"

function Get-Auth {
  Write-Host "== Acquire session token"
  $resp = Invoke-WebRequest -Uri "$Base/session/token" -UseBasicParsing -MaximumRedirection 0 -SessionVariable session
  $cookie = $null
  if ($resp.Headers -and $resp.Headers.ContainsKey('Set-Cookie')) {
    $cookie = ($resp.Headers['Set-Cookie'] | Select-Object -First 1).Split(';')[0]
  }
  if (-not $cookie) {
    $jar = $session.Cookies.GetCookies($Base)
    if ($jar.Count -gt 0) { $cookie = "$($jar[0].Name)=$($jar[0].Value)" }
  }
  if (-not $cookie) { throw "No cookie from /session/token" }
  $token = $cookie -replace '^[^=]+=','' -replace ';.*$',''
  return [pscustomobject]@{
    Cookie  = $cookie
    Token   = $token
    Session = $session
  }
}

$auth = Get-Auth
$Headers = @{ 'X-Session-Token' = $auth.Token; 'Cookie' = $auth.Cookie }

function Invoke-AppJson {
  param(
    [string]$Method,
    [string]$Path,
    $Body
  )
  $params = @{ Uri = "$Base$Path"; Method = $Method; Headers = $Headers; ContentType = 'application/json'; }
  if ($PSBoundParameters.ContainsKey('Body')) {
    $params.Body = ($Body | ConvertTo-Json -Depth 10)
  }
  return Invoke-RestMethod @params
}

function Invoke-AppDelete {
  param(
    [string]$Path
  )
  $resp = Invoke-WebRequest -Uri "$Base$Path" -Method Delete -Headers $Headers -UseBasicParsing -ContentType 'application/json'
  return $resp.StatusCode
}

function Step {
  param(
    [string]$Name,
    [scriptblock]$Run
  )
  try {
    & $Run
    Write-Host "PASS - $Name"
  } catch {
    Write-Host "FAIL - $Name : $($_.Exception.Message)"
    throw
  }
}

$acmeId = $null
$samId = $null
$avaId = $null

Step "POST /app/vendors defaults" {
  $res = Invoke-AppJson -Method Post -Path '/app/vendors' -Body @{ name = 'ACME' }
  if ($res.role -ne 'vendor' -or $res.kind -ne 'org') { throw "Unexpected defaults" }
  $script:acmeId = $res.id
}

Step "POST /app/contacts defaults" {
  $res = Invoke-AppJson -Method Post -Path '/app/contacts' -Body @{ name = 'Sam' }
  if ($res.role -ne 'contact' -or $res.kind -ne 'person') { throw "Unexpected contact defaults" }
  $script:samId = $res.id
}

Step "PUT /app/contacts make both" {
  $res = Invoke-AppJson -Method Put -Path "/app/contacts/$samId" -Body @{ role = 'both' }
  if ($res.role -ne 'both') { throw "Role not both" }
}

Step "Facet delete keep vendor" {
  $res = Invoke-AppJson -Method Put -Path "/app/contacts/$samId" -Body @{ role = 'vendor' }
  if ($res.role -ne 'vendor') { throw "Role not vendor" }
  $code = Invoke-AppDelete -Path "/app/contacts/$samId"
  if ($code -ne 204) { throw "Delete expected 204, got $code" }
}

Step "Create dependent Ava" {
  $res = Invoke-AppJson -Method Post -Path '/app/contacts' -Body @{ name = 'Ava'; kind = 'person'; organization_id = $acmeId }
  if (-not $res.id) { throw "No Ava id" }
  $script:avaId = $res.id
}

Step "Delete org without cascade" {
  $code = Invoke-AppDelete -Path "/app/vendors/$acmeId"
  if ($code -ne 204) { throw "Delete expected 204, got $code" }
  $res = Invoke-AppJson -Method Get -Path "/app/contacts/$avaId"
  if ($res.organization_id -ne $null) { throw "organization_id not null" }
}

Step "Cascade delete Ava2" {
  $resOrg = Invoke-AppJson -Method Post -Path '/app/vendors' -Body @{ name = 'ACME'; role = 'vendor'; kind = 'org' }
  $newOrgId = $resOrg.id
  $resAva = Invoke-AppJson -Method Post -Path '/app/contacts' -Body @{ name = 'Ava2'; kind = 'person'; organization_id = $newOrgId }
  $code = Invoke-AppDelete -Path "/app/vendors/$newOrgId?cascade_children=true"
  if ($code -ne 204) { throw "Cascade delete expected 204" }
  $search = Invoke-AppJson -Method Get -Path '/app/contacts?q=Ava2'
  if ($search -and $search.Length -gt 0) { throw "Ava2 still present" }
}

Write-Host "All smoke steps completed."
