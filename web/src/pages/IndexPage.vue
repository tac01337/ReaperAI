<template>
  <q-page class="flex full-width">
    <div class="full-width row q-gutter-md q-pa-md">
      <div class="col">
        <q-card
          flat
          class="bg-primary"
        >
          <q-list>
            <q-item>
              <q-item-section>
                <q-item-label>Runs</q-item-label>
              </q-item-section>
              <q-item-section side>
              </q-item-section>
            </q-item>
            <q-separator />
            <q-expansion-item
              v-for="(run, index) in data.runs"
              :key="index"
            >
            <template v-slot:header>
              <div class="flex justify-between items-center full-width">
                <div>Run {{ run.id }} on {{ run.host }}</div>
                <q-btn flat round dense icon="delete" @click.stop="confirmDelRunDialog(index)" />
              </div>
            </template>
              <q-card style="overflow-x: scroll;">
                <q-card-section>
                  <pre> {{ JSON.stringify(run, null, 2)  }}</pre>
                </q-card-section>
              </q-card> 
            </q-expansion-item>
          </q-list>
        </q-card>  
      </div>
      <div class="col">
        <q-card
          flat
          class="bg-primary"
        >
          <q-list>
            <q-item>
              <q-item-section>
                <q-item-label>Queries</q-item-label>
              </q-item-section>
              <q-item-section side>
              </q-item-section>
              </q-item>
              <q-separator />
            <q-expansion-item
              v-for="(query, index) in data.queries"
              :key="index"
            >
            <template v-slot:header>
              <div class="flex justify-between items-center full-width">
                <div>Query {{ query.query }}</div>
                <q-btn flat round dense icon="delete" @click.stop="confirmDelQueryDialog(query.id)" />
              </div>
            </template>
              <q-card style="overflow-x: scroll;">
                <q-card-section>
                  <pre> {{ JSON.stringify(query, null, 2)  }}</pre>
                </q-card-section>
              </q-card> 
            </q-expansion-item>
          </q-list>
        </q-card>  
      </div>
      <div class="col">
        <q-card
          flat
          class="bg-primary"
        >
          <q-list>
            <q-item>
              <q-item-section>
                <q-item-label>Commands</q-item-label>
              </q-item-section>
              <q-item-section side>
              </q-item-section>
              </q-item>
              <q-separator />
            <q-expansion-item
              v-for="(command, index) in data.commands"
              :key="index"
              :label="`Commands ${command.name}`"
            >
            <template v-slot:header>
              <div class="flex justify-between items-center full-width">
                <div>Commands {{ command.name }}</div>
                <q-btn flat round dense icon="delete" @click.stop="confirmDelCommandDialog(index)" />
              </div>
            </template>
              <q-card style="overflow-x: auto;">
                <q-card-section>
                  <pre>{{ command.stdout }}</pre>
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </q-list>
        </q-card>  
      </div>
    </div>

    <q-dialog v-model="confirmRun" persistent>
      <q-card>
        <q-card-section class="row items-center">
          <q-avatar icon="delete" color="primary" text-color="white" />
          <span class="q-ml-sm">Are you sure you want to delete this Run?</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn label="Delete" color="negative" v-close-popup @click="deleteRun" />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <q-dialog v-model="confirmQuery" persistent>
      <q-card>
        <q-card-section class="row items-center">
          <q-avatar icon="delete" color="primary" text-color="white" />
          <span class="q-ml-sm">Are you sure you want to delete this Query?</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn label="Delete" color="negative" v-close-popup @click="deleteQuery"/>
        </q-card-actions>
      </q-card>
    </q-dialog>
    <q-dialog v-model="confirmCommand" persistent>
      <q-card>
        <q-card-section class="row items-center">
          <q-avatar icon="delete" color="primary" text-color="white" />
          <span class="q-ml-sm">Are you sure you want to delete this Command?</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn label="Delete" color="negative" v-close-popup @click="deleteCommand" />
        </q-card-actions>
      </q-card>
    </q-dialog>

  </q-page>
</template>

<script>
// import axios from 'axios'
import {api} from 'boot/axios'
import { ref } from 'vue'
export default {
  data() {
    return {
      data: {
        runs: [],
        queries: [],
        commands: []
      },
      confirmRun: ref(false),
      confirmQuery: ref(false),
      confirmCommand: ref(false),
      
      selectedRun: null,
      selectedQuery: null,
      selectedCommand: null,
    }
  },
  methods: {
    async fetchData() {

      var response = await api.get('/api/runs')
      this.data.runs = response.data

      var qres = await api.get('/api/queries')
      // console.log(qres.data)
      this.data.queries = qres.data

      var cres = await api.get('/api/commands')
      this.data.commands = cres.data
      // this.console.log(this.data)
    },

    confirmDelCommandDialog(index) {
      this.confirmCommand = true
      this.selectedCommand = index
    },
    confirmDelQueryDialog(index) {
      this.confirmQuery = true
      this.selectedQuery = index
    },
    confirmDelRunDialog(index) {
      this.confirmRun = true
      this.selectedRun = index
    },

    async deleteCommand() {

      const command = this.data.commands[this.selectedCommand]
      await api.delete(`api/commands?id=eq.${command.id}`)
      this.data.commands.splice(this.selectedCommand, 1)
    },
    async deleteQuery() {
      const query = this.data.queries[this.selectedQuery]
      await api.delete(`api/queries?id=eq.${query.id}`)
      this.data.queries.splice(this.selectedQuery, 1)
    },
    async deleteRun() {
      const run = this.data.runs[this.selectedRun]
      await api.delete(`api/runs?id=eq.${run.id}`)
      this.data.runs.splice(this.selectedRun, 1)
    }
  },
  mounted() {
    this.fetchData()
    setInterval(() => {
      this.fetchData()
    }, 5000)
  }
}

</script>
