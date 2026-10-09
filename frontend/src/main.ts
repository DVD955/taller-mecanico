import { createApp } from 'vue'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import App from './App.vue'
import './styles.css'

const vuetify = createVuetify({
  defaults: {
    VBtn: { elevation: 0, rounded: 'lg' },
    VTextField: { rounded: 'lg' },
    VTextarea: { rounded: 'lg' },
    VSelect: { rounded: 'lg' },
    VAutocomplete: { rounded: 'lg' },
    VFileInput: { rounded: 'lg' },
  },
  theme: {
    defaultTheme: 'tallerTheme',
    themes: {
      tallerTheme: {
        dark: false,
        colors: {
          primary: '#FAEBD7',
          secondary: '#2F4F4F',
          surface: '#FAEBD7',
          background: '#FAEBD7',
          'on-surface': '#2F4F4F',
          'on-background': '#2F4F4F',
          'on-primary': '#2F4F4F',
          'on-secondary': '#FAEBD7',
          error: '#B3261E',
          success: '#2E7D32',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
