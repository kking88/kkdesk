<script setup>
const projectName = "__PROJECT_NAME__";
const repoUrl = "https://github.com/__OWNER__/__REPO_NAME__";
</script>

<template>
  <main class="container">
    <h1>{{ projectName }}</h1>
    <p>Vue + Vite project created by GitHub Project Factory.</p>
    <a :href="repoUrl" target="_blank" rel="noreferrer">Open Repository</a>
  </main>
</template>

<style scoped>
.container {
  font-family: "Avenir", "Helvetica Neue", Helvetica, Arial, sans-serif;
  max-width: 720px;
  margin: 4rem auto;
  padding: 0 1rem;
  text-align: center;
  line-height: 1.6;
}

h1 {
  margin-bottom: 1rem;
}

a {
  color: #2f6feb;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>
