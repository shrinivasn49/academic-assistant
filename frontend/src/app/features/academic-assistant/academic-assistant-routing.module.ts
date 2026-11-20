import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AssistantPageComponent } from './pages/assistant-page/assistant-page.component';

const routes: Routes = [
  {
    path: '',
    component: AssistantPageComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AcademicAssistantRoutingModule {}