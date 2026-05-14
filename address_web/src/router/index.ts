import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import RecordsView from '../views/RecordsView.vue'
import ResultDetailView from '../views/ResultDetailView.vue'
import ValidationRulesView from '../views/ValidationRulesView.vue'
import SplitView from '../views/SplitView.vue'
import EnvironmentView from '../views/EnvironmentView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', redirect: '/split' },
        { path: 'split', component: SplitView },
        { path: 'validation-rules', component: ValidationRulesView },
        { path: 'records', component: RecordsView },
        { path: 'records/:id', component: ResultDetailView },
        { path: 'environment', component: EnvironmentView },
      ],
    },
  ],
})

export default router
