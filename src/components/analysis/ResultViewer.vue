<template>
  <div class="result-viewer">
    <div class="result-output" v-if="result">
      <pre>{{ result }}</pre>
    </div>
    <div class="result-visual" v-if="visualUrl">
      <img :src="visualUrl" alt="结果可视化" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  result?: string
  visualUrl?: string
}>()
</script>

<style scoped>
.result-viewer {
  height: 100%;
}

.result-output {
  background: rgba(0, 0, 0, 0.5);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  max-height: 400px;
}

.result-visual img {
  max-width: 100%;
  border-radius: 6px;
  margin-top: 10px;
}
</style>