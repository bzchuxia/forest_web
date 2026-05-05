<template>
  <div class="algorithm-card" @click="$emit('run')">
    <div class="card-icon">
      <slot name="icon">
        <i class="fas fa-cogs"></i>
      </slot>
    </div>
    <h4>{{ title }}</h4>
    <p>{{ desc }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  desc: string
}>()

defineEmits<{
  run: []
}>()
</script>

<style scoped>
.algorithm-card {
  background: rgba(0, 20, 50, 0.95);
  border-radius: 8px;
  padding: 20px;
  color: #fff;
  cursor: pointer;
  transition: all 0.3s ease;
}

.algorithm-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(79, 195, 247, 0.2);
}

.card-icon {
  font-size: 24px;
  color: #4fc3f7;
  margin-bottom: 10px;
}

h4 {
  margin-bottom: 10px;
  font-size: 16px;
}

p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}
</style>