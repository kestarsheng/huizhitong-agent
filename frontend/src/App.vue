<script setup>
import { computed, onMounted, ref } from 'vue'

const tools = ref([])
const loading = ref(true)
const error = ref('')
const active = computed(() => tools.value.filter(item => item.enabled === 1).length)

async function loadTools() {
  loading.value = true
  try {
    const response = await fetch('http://localhost:8083/internal/tools')
    if (!response.ok) throw new Error('工具服务暂不可用')
    tools.value = await response.json()
    error.value = ''
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

onMounted(loadTools)
</script>

<template>
  <main class="shell">
    <aside class="rail"><div class="mark">HZ</div><div class="rail-label">汇智通<br><span>AI CONTROL</span></div><nav><a class="selected">工具目录</a><a>智能体</a><a>知识库</a><a>调用审计</a></nav><div class="rail-foot">LOCAL / DEV</div></aside>
    <section class="content">
      <header><div><p class="eyebrow">CONTROL ROOM / TOOL REGISTRY</p><h1>工具目录</h1><p class="sub">统一查看 MCP Server 暴露给智能体的业务能力。</p></div><button @click="loadTools">刷新目录 ↻</button></header>
      <div class="stats"><div><span>已注册工具</span><strong>{{ tools.length }}</strong></div><div><span>当前启用</span><strong>{{ active }}</strong></div><div><span>连接状态</span><strong class="online">{{ error ? 'OFFLINE' : 'ONLINE' }}</strong></div></div>
      <div v-if="loading" class="empty">正在读取工具注册中心…</div>
      <div v-else-if="error" class="empty danger">{{ error }}<button @click="loadTools">重试</button></div>
      <div v-else class="tool-grid"><article v-for="tool in tools" :key="tool.id" class="tool-card"><div class="card-top"><span class="tool-id">TOOL / {{ String(tool.id).padStart(2, '0') }}</span><i :class="['dot', tool.enabled === 1 ? 'on' : 'off']"></i></div><h2>{{ tool.toolName }}</h2><p>{{ tool.description }}</p><div class="server">↳ {{ tool.serverName }} <span>{{ tool.enabled === 1 ? '已启用' : '已停用' }}</span></div></article></div>
    </section>
  </main>
</template>
