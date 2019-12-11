import os, pickle, copy, datetime
from connect import *


def load_obj(path):
    if path[-4:] != '.pkl':
        path += '.pkl'
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        out = {}
        return out


def save_obj(obj, path): # Save almost anything.. dictionary, list, etc.
    if path[-4:] != '.pkl':
        path += '.pkl'
    with open(path, 'wb') as f:
        pickle.dump(obj, f, pickle.DEFAULT_PROTOCOL)
    return None


class Patient_DB_Structure():
    def __init__(self):
        self.patient_db = get_current("PatientDB")
        self.db_name = 'Chung'
        self.ui = get_current("ui")
        self.application_version = self.ui.GetApplicationVersion()
        self.path = '\\\\mymdafiles\\di_data1\\Morfeus\\bmanderson\\CNN\\Data\\Raystation_Data\\Raystation' + \
                           self.db_name + '_' + self.application_version
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.status_path = self.path
        if not os.path.exists(self.status_path + '_Error\\'):
            os.makedirs(self.status_path + '_Error\\')

        # Get all the patients
        self.all_patients = self.patient_db.QueryPatientInfo(Filter={})
        self.run()

    def run(self):
        for self.info in self.all_patients:
            self.MRN = self.info['PatientID']
            self.patient_name = self.info['DisplayName']
            if os.path.exists(os.path.join(self.path,self.MRN + '$$' + self.patient_name + '.pkl')):
                continue
            self.data_dict = {'Name':self.patient_name,'MRN':self.MRN}
            if self.MRN in self.data_dict.keys():
                continue
            try:
                self.patient = self.patient_db.LoadPatient(PatientInfo=self.info, AllowPatientUpgrade=True)
            except:
                continue
            for self.case in self.patient.Cases:
                self.data_dict[self.case.CaseName] = {}
                self.rois_in_case = []
                for roi in self.case.PatientModel.RegionsOfInterest:
                    self.rois_in_case.append(roi.Name)
                for self.exam in self.case.Examinations:
                    self.data_dict[self.case.CaseName][self.exam.Name] = self.get_available_data()
            try:
                save_obj(self.data_dict,os.path.join(self.path,self.MRN + '$$' + self.patient_name + '.pkl'))
            except:
                fid = open(os.path.join(self.path+'_Error\\',self.patient_name + 'Error.txt'),'w+')
                fid.close()
                continue


    def ChangePatient(self):
        info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": self.MRN}, UseIndexService=False)
        if not info_all:
            info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": self.MRN}, UseIndexService=True)
        info = []
        for info_temp in info_all:
            if info_temp['PatientID'] == self.MRN:
                info = info_temp
                break
        self.patient = self.patient_db.LoadPatient(PatientInfo=info, AllowPatientUpgrade=True)

    def get_available_data(self):
        data = dict()
        data['Modality'] = str(self.exam.EquipmentInfo.Modality)
        date = self.exam.GetExaminationDateTime()
        if date:
            data['Date_Time'] = str(date.Year) + '\\' + str(date.Month) + '\\' + str(date.Day) + '\\' + str(date.Hour) + \
                                '\\' + str(date.Minute) + '\\' + str(date.Second)
        data['rois'] = {}
        dicom_data = self.exam.GetAcquisitionDataFromDicom()
        data['Description'] = dicom_data['SeriesModule']['SeriesDescription']
        data['SeriesInstanceUID'] = dicom_data['SeriesModule']['SeriesInstanceUID']
        data['Protocol'] = self.exam.GetProtocolName()
        for roi in self.rois_in_case:
            data['rois'][roi] = {'Volume':0,'Intensity':{'Min':0,'Max':0,'Average':0}}
            try: # Actually 2x faster to do it this way, than the HasContours() method
                data['rois'][roi]['Volume'] = self.case.PatientModel.StructureSets[self.exam.Name].RoiGeometries[roi].GetRoiVolume()
                intensity_stats = self.case.Examinations[self.exam.Name].Series[0].ImageStack.GetIntensityStatistics(RoiName=roi)
                for key in ['Min','Max','Average']:
                    for val in intensity_stats[key]:
                        data['rois'][roi]['Intensity'][key] = val.Key #Raystation puts the key/value pair as answer:HU, so this is necessary
            except:
                continue
        return data


Patient_DB_Structure()