import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'academic-assistant',
    pathMatch: 'full'
  },
  {
    path: 'academic-assistant',
    loadChildren: () =>
      import('./features/academic-assistant/academic-assistant.module')
        .then(m => m.AcademicAssistantModule)
  },
  {
    path: '**',
    redirectTo: 'academic-assistant'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}