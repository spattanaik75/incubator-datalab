/***************************************************************************

Copyright (c) 2016, EPAM SYSTEMS INC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

****************************************************************************/

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgDateRangePickerModule } from 'ng-daterangepicker';

import { MaterialModule } from './../shared/material.module';
import { FormControlsModule } from './../shared/form-controls';
import { ReportingComponent } from './reporting.component';
import { NavbarModule, ModalModule, UploadKeyDialogModule, ProgressDialogModule } from './../shared';
import { KeysPipeModule, LineBreaksPipeModule } from './../core/pipes';
import { ReportingGridComponent } from './reporting-grid/reporting-grid.component';
import { ToolbarComponent } from './toolbar/toolbar.component';

@NgModule({
  imports: [
    CommonModule,
    ModalModule,
    NavbarModule,
    FormControlsModule,
    KeysPipeModule,
    LineBreaksPipeModule,
    NgDateRangePickerModule,
    UploadKeyDialogModule,
    ProgressDialogModule,
    MaterialModule
  ],
  declarations: [
    ReportingComponent,
    ReportingGridComponent,
    ToolbarComponent
  ],
  exports: [ReportingComponent]
})
export class ReportingModule { }