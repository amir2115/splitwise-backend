import { createApp } from 'vue'

import App from '@/app/App.vue'
import { router } from '@/app/router'
import '@/shared/styles/tokens.css'
import '@/shared/styles/app.css'

document.documentElement.lang = 'fa'
document.documentElement.dir = 'rtl'

const app = createApp(App)
app.use(router)
app.mount('#app')
