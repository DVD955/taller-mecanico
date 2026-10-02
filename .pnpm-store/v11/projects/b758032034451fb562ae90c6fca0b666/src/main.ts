import { createApp } from 'vue'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import './styles.css'

const vuetify = createVuetify({
  theme: {
    defaultTheme: 'tallerTheme',
    themes: {
      tallerTheme: {
        dark: false,
        colors: {
          primary: '#FAEBD7',
          secondary: '#2F4F4F',
          surface: '#FFFDF9',
          background: '#FAEBD7',
          error: '#B3261E',
          success: '#2E7D32',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
