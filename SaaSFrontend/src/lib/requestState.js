// 对后端、设置和请求代次做快照，过滤切换或重复请求后的旧结果。
export function createRequestState(settings) {
  // generation 表示当前连接/会话这一代；invalidate 让之前的返回值过期，但不撤销已执行的服务器操作。
  let generation = 0
  let sequence = 0
  const latest = new Map()
  return {
    invalidate() { generation += 1 },
    // slot 将 health、stats、monitor 等请求分开比较新旧，避免不同面板互相使请求失效。
    begin(slot) {
      const revision = generation
      const id = ++sequence
      const backend = settings.backend
      // 复制 endpoints 防止原对象被修改后连快照也跟着变化；异步结果必须与发起时的配置对应。
      const snapshot = { ...settings, endpoints: { ...settings.endpoints } }
      latest.set(slot, id)
      return {
        backend,
        settings: snapshot,
        isCurrent: () => revision === generation && latest.get(slot) === id &&
          backend === settings.backend && snapshot.endpoints[backend] === settings.endpoints[backend]
      }
    }
  }
}
