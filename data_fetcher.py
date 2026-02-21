from pesuacademy import PESUAcademy
async def fetch_student_data(username:str,password:str) -> dict:
        '''function to log into PESU website and return awaited, sstructured data. exception if fails'''
        pesu=None
        try:
                pesu= await PESUAcademy.login(username=username, password=password)
                
                import asyncio
                attendance_data, timetable_data, profile_data =await asyncio.gather(
                        pesu.get_attendance(),
                        pesu.get_timetable(),
                        pesu.get_profile(),
                )
                return {
                        "username": username,
                        "attendance":_serialize_attendance(attendance_data),
                        "timetable":_serialize_attendance(timetable_data),
                        "profile":_serialize_attendance(profile_data),
                }
        except Exception as e:
                raise Exception(f"PESU fetch failed: {e}")
        finally:
                if pesu:
                        await pesu.close()
def _serialize_attendance(data:dict) ->dict:
        result={}
        for semester,courses in data.items():
                result[(str)semester]= [course.model_dump() for course in courses]
        return result

def _serialize_timetable 

                