/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ImagesService } from '../../images/images.service';
import { ShareModalData, Toaster_Message } from '../../images';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'datalab-share-image-dialog',
  templateUrl: './share-image-dialog.component.html',
  styleUrls: ['./share-image-dialog.component.scss']
})
export class ShareImageDialogComponent implements OnInit{
  imageName!: string;

  constructor(
    public dialogRef: MatDialogRef<ShareImageDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ShareModalData,
    private imagesService: ImagesService,
    private toastr: ToastrService,
  ) { }

  ngOnInit() {
    this.imageName = this.data.image.name;
  }

  onShare() {
    this.dialogRef.close();
    this.imagesService.shareImageAllUsers(this.data.image)
      .subscribe(
      () => this.toastr.success(Toaster_Message.successShare, 'Success!')
    );
  }
}
