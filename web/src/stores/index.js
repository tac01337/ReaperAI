import { store } from 'quasar/wrappers'
import { createPinia } from 'pinia'

/*
 * If not building with SSR mode, you can
 * directly export the Store instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Store instance.
 */

export default store((/* { ssrContext } */) => {
  const pinia = createPinia()

  async function fetchData() {
    let response;
    response = api.get('/api/runs');
    const runs = response.data;
    console.log(runs)
    response = api.get('/api/queries');
    const queries = response.data;
  
    response = api.get('/api/commands');
    const commands = response.data;
  
    response = api.get('/api/scan_results');
    const scan_results = response.data;
  
    response = api.get('/api/services');
    const services = response.data;
  
    response = api.get('/api/ports');
    const ports = response.data;
  
    response = api.get('/api/exploits');
    const exploits = response.data;
  
    response = api.get('/api/vulnerabilities'); 
    const vulnerabilities = response.data;
  
    return {
      runs,
      queries,
      commands,
      scan_results,
      services,
      ports,
      exploits,
      vulnerabilities
    };
  }

  // You can add Pinia plugins here
  // pinia.use(SomePiniaPlugin)

  return pinia
})
