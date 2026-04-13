import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const repoName = process.env.GITHUB_REPOSITORY?.split("/")[1] || "__REPO_NAME__";
const isGithubActions = process.env.GITHUB_ACTIONS === "true";

export default defineConfig({
  plugins: [vue()],
  base: isGithubActions ? `/${repoName}/` : "/",
});
