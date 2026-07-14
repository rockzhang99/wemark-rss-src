export const getToken = (): string | null => {
  return localStorage.getItem('token')
}

// 解析 JWT payload（无需密钥，payload 为 base64url 编码）
export const parseJwt = (token: string): any | null => {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

// 本地判断 token 是否已过期（无需请求后端）
// 留 10 秒缓冲，避免临界时刻的误判
export const isTokenExpired = (): boolean => {
  const token = getToken()
  if (!token) return true
  const payload = parseJwt(token)
  if (!payload || typeof payload.exp !== 'number') return true
  return Date.now() >= payload.exp * 1000 - 10000
}